from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
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

router = APIRouter(prefix="/api/ehr", tags=["Clinical EHR"])

class BookAppointmentRequest(BaseModel):
    patient_id: str
    procedure_type: str = "colonoscopy"
    slot_datetime: str
    provider_id: str = "PR101"
    notes: Optional[str] = None

class RescheduleAppointmentRequest(BaseModel):
    new_slot_datetime: str
    reason: Optional[str] = "Patient requested change"

class SetFaultRequest(BaseModel):
    fault_type: Optional[str] = None  # "TIMEOUT", "SLOT_UNAVAILABLE", "MISSING_INFO", None

@router.get("/patients/{id}", response_model=Patient)
async def get_patient(id: str, requester_id: str = Query("P101"), role: UserRole = Query(UserRole.PATIENT)):
    try:
        return await ehr_service.get_patient_async(id, requester_id=requester_id, role=role)
    except EHRError as e:
        raise HTTPException(status_code=403 if e.code == "ACCESS_DENIED" else 404, detail=e.message)

@router.get("/appointments/{id}", response_model=Appointment)
async def get_appointment(id: str, requester_id: str = Query("P101"), role: UserRole = Query(UserRole.PATIENT)):
    try:
        return await ehr_service.get_appointment_async(id, requester_id=requester_id, role=role)
    except EHRError as e:
        raise HTTPException(status_code=403 if e.code == "ACCESS_DENIED" else 404, detail=e.message)

@router.get("/appointments/availability")
async def get_availability(
    procedure_type: str = Query("colonoscopy"),
    provider_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    try:
        slots = await ehr_service.search_available_slots_async(procedure_type, provider_id, start_date, end_date)
        return {"slots": slots, "count": len(slots)}
    except EHRError as e:
        raise HTTPException(status_code=504 if e.code == "API_TIMEOUT" else 400, detail=e.message)

@router.post("/appointments", response_model=Appointment, status_code=status.HTTP_201_CREATED)
async def book_appointment(req: BookAppointmentRequest):
    try:
        return await ehr_service.book_appointment_async(
            patient_id=req.patient_id,
            procedure_type=req.procedure_type,
            slot_datetime_str=req.slot_datetime,
            provider_id=req.provider_id,
            notes=req.notes
        )
    except SlotUnavailableError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except ApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except EHRError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.patch("/appointments/{id}", response_model=Appointment)
async def reschedule_appointment(id: str, req: RescheduleAppointmentRequest):
    try:
        return await ehr_service.reschedule_appointment_async(
            appointment_id=id,
            new_slot_datetime_str=req.new_slot_datetime,
            reason=req.reason or "Patient request"
        )
    except SlotUnavailableError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except EHRError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.delete("/appointments/{id}", response_model=Appointment)
async def cancel_appointment(id: str, reason: str = Query("Patient cancellation")):
    try:
        return await ehr_service.cancel_appointment_async(appointment_id=id, reason=reason)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ApiTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except EHRError as e:
        raise HTTPException(status_code=400, detail=e.message)

@router.get("/patients/{id}/procedures")
async def get_patient_procedures(id: str):
    appts = await ehr_service.get_patient_appointments_async(id)
    return {"patient_id": id, "appointments": appts}

@router.get("/prep-protocols/{procedure}", response_model=Optional[PrepProtocol])
async def get_prep_protocol(procedure: str):
    protocol = await ehr_service.get_prep_protocol_async(procedure)
    if not protocol:
        raise HTTPException(status_code=404, detail=f"No prep protocol found for procedure '{procedure}'.")
    return protocol

@router.get("/snapshot")
async def get_ehr_snapshot():
    """Returns complete current database state for real-time inspection."""
    return await ehr_service.take_snapshot_async()

@router.post("/fault-injection")
def set_fault_injection(req: SetFaultRequest):
    """Set or clear test fault injection."""
    ehr_service.forced_failure = req.fault_type
    return {"status": "SUCCESS", "current_fault": ehr_service.forced_failure}

@router.post("/reset")
async def reset_ehr():
    """Reset EHR database to baseline synthetic practice records."""
    ehr_service.forced_failure = None
    await seed_database(force=True)
    return {"status": "SUCCESS", "message": "Clinical EHR database reset to clean baseline."}
