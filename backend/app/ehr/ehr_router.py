from datetime import datetime, timezone
import re
import traceback
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Header, Request, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator

from .ehr_service import (
    ehr_service,
    EHRError,
    SlotUnavailableError,
    AppointmentNotFoundError,
    ApiTimeoutError,
    ConflictingAppointmentError,
    MissingPatientInfoError
)
from ..models.ehr import Patient, Appointment, PrepProtocol
from ..models.audit import UserRole
from ..db.seed import seed_database
from ..security.auth import security_bearer, decode_access_token
from ..security.rbac import verify_permission, check_permission
from ..security.rate_limiter import enforce_rate_limit
from ..security.idempotency import idempotency_cache
from ..db.database import get_db_session
from ..db.models import AuditEvent as AuditEventModel

router = APIRouter(prefix="/api/ehr", tags=["Clinical EHR"])

class BookAppointmentRequest(BaseModel):
    patient_id: str = Field(..., min_length=2, max_length=64)
    procedure_type: str = Field("colonoscopy", min_length=3, max_length=64)
    slot_datetime: str = Field(..., description="ISO-8601 UTC slot datetime")
    provider_id: str = Field("PR101", min_length=2, max_length=64)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("patient_id", "provider_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_-]+$", v.strip()):
            raise ValueError("ID must be alphanumeric with hyphens or underscores.")
        return v.strip()

    @field_validator("slot_datetime")
    @classmethod
    def validate_future_date(cls, v: str) -> str:
        clean = v.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Must not be in the past
            if dt < datetime.now(timezone.utc):
                raise ValueError("Appointment datetime cannot be in the past.")
        except Exception as e:
            if "in the past" in str(e):
                raise
            raise ValueError("Invalid ISO-8601 datetime format for slot_datetime.")
        return v

class RescheduleAppointmentRequest(BaseModel):
    new_slot_datetime: str = Field(..., description="New ISO-8601 UTC datetime")
    reason: Optional[str] = Field("Patient requested change", max_length=500)

    @field_validator("new_slot_datetime")
    @classmethod
    def validate_future_date(cls, v: str) -> str:
        clean = v.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < datetime.now(timezone.utc):
                raise ValueError("Appointment datetime cannot be in the past.")
        except Exception as e:
            if "in the past" in str(e):
                raise
            raise ValueError("Invalid ISO-8601 datetime format for new_slot_datetime.")
        return v

class SetFaultRequest(BaseModel):
    fault_type: Optional[str] = Field(None, max_length=32)

def get_optional_auth_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except Exception:
        return None

def enforce_patient_boundary(requester_claims: Optional[Dict[str, Any]], target_patient_id: str):
    """Ensure PATIENT role can only view or modify their own patient record."""
    if not requester_claims:
        return  # In open public demo endpoints without auth, fallback to internal scoping
    role = requester_claims.get("role", "PATIENT").upper()
    user_patient_id = requester_claims.get("patient_id") or requester_claims.get("sub")
    if role == "PATIENT" and user_patient_id and user_patient_id != target_patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Patient '{user_patient_id}' cannot access records for patient '{target_patient_id}'."
        )

@router.get("/patients/{id}", response_model=Patient)
async def get_patient(
    id: str,
    request: Request,
    requester_id: str = Query("P101"),
    role: UserRole = Query(UserRole.PATIENT),
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    enforce_rate_limit(request, max_requests=60, window_seconds=60, operation="get_patient")
    # Authorization boundary check
    if auth_claims:
        requester_id = auth_claims.get("patient_id") or auth_claims.get("sub", requester_id)
        role_str = auth_claims.get("role", "PATIENT").upper()
        role = UserRole.ADMIN if role_str == "ADMIN" else (UserRole.STAFF if role_str in ("STAFF", "CLINICIAN") else UserRole.PATIENT)
    enforce_patient_boundary(auth_claims, id)

    try:
        return await ehr_service.get_patient_async(id, requester_id=requester_id, role=role)
    except EHRError as e:
        raise HTTPException(status_code=403 if e.code == "ACCESS_DENIED" else 404, detail=e.message)

@router.get("/appointments/{id}", response_model=Appointment)
async def get_appointment(
    id: str,
    request: Request,
    requester_id: str = Query("P101"),
    role: UserRole = Query(UserRole.PATIENT),
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    enforce_rate_limit(request, max_requests=60, window_seconds=60, operation="get_appointment")
    if auth_claims:
        requester_id = auth_claims.get("patient_id") or auth_claims.get("sub", requester_id)
        role_str = auth_claims.get("role", "PATIENT").upper()
        role = UserRole.ADMIN if role_str == "ADMIN" else (UserRole.STAFF if role_str in ("STAFF", "CLINICIAN") else UserRole.PATIENT)

    try:
        appt = await ehr_service.get_appointment_async(id, requester_id=requester_id, role=role)
        enforce_patient_boundary(auth_claims, appt.patient_id)
        return appt
    except EHRError as e:
        raise HTTPException(status_code=403 if e.code == "ACCESS_DENIED" else 404, detail=e.message)

@router.get("/appointments/availability")
async def get_availability(
    request: Request,
    procedure_type: str = Query("colonoscopy"),
    provider_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    enforce_rate_limit(request, max_requests=60, window_seconds=60, operation="availability")
    try:
        slots = await ehr_service.search_available_slots_async(procedure_type, provider_id, start_date, end_date)
        return {"slots": slots, "count": len(slots)}
    except EHRError as e:
        raise HTTPException(status_code=504 if e.code == "API_TIMEOUT" else 400, detail=e.message)

@router.post("/appointments", response_model=Appointment, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    req: BookAppointmentRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    enforce_rate_limit(request, max_requests=30, window_seconds=60, operation="book_appointment")
    enforce_patient_boundary(auth_claims, req.patient_id)

    # Check idempotency cache
    if idempotency_key:
        cached = idempotency_cache.get(idempotency_key)
        if cached:
            return cached["result"]

    try:
        appt = await ehr_service.book_appointment_async(
            patient_id=req.patient_id,
            procedure_type=req.procedure_type,
            slot_datetime_str=req.slot_datetime,
            provider_id=req.provider_id,
            notes=req.notes
        )
        if idempotency_key:
            idempotency_cache.set(idempotency_key, appt, status_code=201)
        return appt
    except SlotUnavailableError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except ApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except EHRError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.patch("/appointments/{id}", response_model=Appointment)
async def reschedule_appointment(
    id: str,
    req: RescheduleAppointmentRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    enforce_rate_limit(request, max_requests=30, window_seconds=60, operation="reschedule_appointment")
    if idempotency_key:
        cached = idempotency_cache.get(idempotency_key)
        if cached:
            return cached["result"]

    try:
        # Pre-verify patient ownership if authenticated
        existing = await ehr_service.get_appointment_async(id, requester_id="SYSTEM", role=UserRole.ADMIN)
        enforce_patient_boundary(auth_claims, existing.patient_id)

        appt = await ehr_service.reschedule_appointment_async(
            appointment_id=id,
            new_slot_datetime_str=req.new_slot_datetime,
            reason=req.reason or "Patient request"
        )
        if idempotency_key:
            idempotency_cache.set(idempotency_key, appt, status_code=200)
        return appt
    except SlotUnavailableError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except EHRError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.delete("/appointments/{id}", response_model=Appointment)
async def cancel_appointment(
    id: str,
    request: Request,
    reason: str = Query("Patient cancellation"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    enforce_rate_limit(request, max_requests=30, window_seconds=60, operation="cancel_appointment")
    if idempotency_key:
        cached = idempotency_cache.get(idempotency_key)
        if cached:
            return cached["result"]

    try:
        existing = await ehr_service.get_appointment_async(id, requester_id="SYSTEM", role=UserRole.ADMIN)
        enforce_patient_boundary(auth_claims, existing.patient_id)

        appt = await ehr_service.cancel_appointment_async(appointment_id=id, reason=reason)
        if idempotency_key:
            idempotency_cache.set(idempotency_key, appt, status_code=200)
        return appt
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except EHRError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.get("/patients/{id}/procedures")
async def get_patient_procedures(
    id: str,
    request: Request,
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    enforce_rate_limit(request, max_requests=60, window_seconds=60, operation="patient_procedures")
    enforce_patient_boundary(auth_claims, id)
    appts = await ehr_service.get_patient_appointments_async(id)
    return {"patient_id": id, "appointments": appts}

@router.get("/prep-protocols/{procedure}", response_model=Optional[PrepProtocol])
async def get_prep_protocol(procedure: str, request: Request):
    enforce_rate_limit(request, max_requests=60, window_seconds=60, operation="get_prep_protocol")
    protocol = await ehr_service.get_prep_protocol_async(procedure)
    if not protocol:
        raise HTTPException(status_code=404, detail=f"No prep protocol found for procedure '{procedure}'.")
    return protocol

@router.get("/snapshot")
async def get_ehr_snapshot(
    request: Request,
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    """Returns complete current database state for real-time inspection."""
    enforce_rate_limit(request, max_requests=30, window_seconds=60, operation="snapshot")
    if auth_claims:
        role = auth_claims.get("role", "PATIENT").upper()
        if role == "PATIENT":
            raise HTTPException(status_code=403, detail="Access Denied: Patients cannot inspect global system snapshots.")
    return await ehr_service.take_snapshot_async()

@router.post("/fault-injection")
def set_fault_injection(
    req: SetFaultRequest,
    request: Request,
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    """Set or clear test fault injection. Restricted to non-patient users."""
    enforce_rate_limit(request, max_requests=10, window_seconds=60, operation="fault_injection")
    if auth_claims:
        role = auth_claims.get("role", "PATIENT").upper()
        if role == "PATIENT":
            raise HTTPException(status_code=403, detail="Access Denied: Patients cannot alter fault injection state.")
    ehr_service.forced_failure = req.fault_type
    return {"status": "SUCCESS", "current_fault": ehr_service.forced_failure}

@router.post("/reset")
async def reset_ehr(
    request: Request,
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    """Reset EHR database to baseline synthetic practice records. Protected with audit logging."""
    enforce_rate_limit(request, max_requests=5, window_seconds=60, operation="reset_ehr")
    user_id = "ANONYMOUS_DEV"
    role = "SYSTEM"
    if auth_claims:
        role = auth_claims.get("role", "PATIENT").upper()
        user_id = auth_claims.get("sub", "UNKNOWN")
        if role == "PATIENT":
            raise HTTPException(status_code=403, detail="Access Denied: Patients cannot execute destructive EHR database resets.")

    ehr_service.forced_failure = None
    try:
        await seed_database(force=True)
    except Exception as seed_err:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Seed failed: {type(seed_err).__name__}: {seed_err}\n{tb[-1500:]}"
        )

    # Record immutable audit event for destructive operation
    try:
        async with get_db_session() as session:
            evt = AuditEventModel(
                event_type="DATABASE_RESET",
                user_id=user_id,
                role=role,
                action_name="RESET_EHR_BASELINE",
                status="SUCCESS",
                client_ip=request.client.host if request.client else "unknown",
                details={"reason": "Manual baseline reset"}
            )
            session.add(evt)
            await session.commit()
    except Exception:
        pass

    return {"status": "SUCCESS", "message": "Clinical EHR database reset to clean baseline."}
