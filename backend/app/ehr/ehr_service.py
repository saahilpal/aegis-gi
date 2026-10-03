import uuid
import copy
import asyncio
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, update, delete, and_, func

from ..db.database import get_db_session
from ..db.models import (
    Patient as PatientModel,
    Provider as ProviderModel,
    Procedure as ProcedureModel,
    Appointment as AppointmentModel,
    PrepProtocol as PrepProtocolModel,
    AuditEvent as AuditEventModel,
)
from ..models.ehr import Patient, Provider, Appointment, Procedure, PrepProtocol, WorkflowEvent
from ..models.audit import AuditEvent, UserRole

class EHRError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

class SlotUnavailableError(EHRError):
    def __init__(self, msg: str = "Requested appointment slot is no longer available."):
        super().__init__("SLOT_UNAVAILABLE", msg)

class AppointmentNotFoundError(EHRError):
    def __init__(self, msg: str = "Appointment record could not be found."):
        super().__init__("APPOINTMENT_NOT_FOUND", msg)

class ApiTimeoutError(EHRError):
    def __init__(self, msg: str = "Downstream EHR gateway timed out (504 Gateway Timeout)."):
        super().__init__("API_TIMEOUT", msg)

class ConflictingAppointmentError(EHRError):
    def __init__(self, msg: str = "Patient already has an active overlapping appointment on this date."):
        super().__init__("CONFLICTING_APPOINTMENT", msg)

class MissingPatientInfoError(EHRError):
    def __init__(self, msg: str = "Patient identifier or required clinical demographic missing."):
        super().__init__("MISSING_PATIENT_INFO", msg)


def run_async(coro):
    """Safely execute an async coroutine from synchronous contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result(timeout=15)
    else:
        return asyncio.run(coro)


class EHRService:
    """
    Production Database-Backed Clinical EHR Service.
    Persists patients, appointments, providers, procedures, prep protocols,
    and HIPAA audit events directly to PostgreSQL (or SQLite async).
    """

    def __init__(self):
        # Ephemeral runtime cache for fault injection during evaluation/testing
        self.forced_failure: Optional[str] = None

    # ==================== Async Core Operations ====================

    async def get_patient_async(self, patient_id: str, requester_id: str = "P101", role: UserRole = UserRole.PATIENT) -> Patient:
        if role == UserRole.PATIENT and requester_id != patient_id:
            await self.log_audit_async(requester_id, role, "READ_PATIENT", "Patient", patient_id, "DENIED", "RBAC cross-patient access attempt")
            raise EHRError("ACCESS_DENIED", "Access denied: Patients cannot access other patient records.")

        async with get_db_session() as session:
            stmt = select(PatientModel).where(PatientModel.id == patient_id)
            res = await session.execute(stmt)
            p = res.scalar_one_or_none()
            if not p:
                await self.log_audit_async(requester_id, role, "READ_PATIENT", "Patient", patient_id, "NOT_FOUND")
                raise MissingPatientInfoError(f"Patient ID {patient_id} does not exist.")

            await self.log_audit_async(requester_id, role, "READ_PATIENT", "Patient", patient_id, "SUCCESS")
            med_hist = p.medical_history or {}
            return Patient(
                id=p.id,
                mrn=p.mrn,
                first_name=p.first_name,
                last_name=p.last_name,
                dob=p.dob,
                gender=med_hist.get("gender", "Female"),
                phone=p.phone or "",
                email=p.email or "",
                medical_conditions=med_hist.get("medical_conditions", []),
                allergies=med_hist.get("allergies", []),
                current_medications=med_hist.get("current_medications", []),
                portal_access=med_hist.get("portal_access", True)
            )

    async def get_appointment_async(self, appointment_id: str, requester_id: str = "P101", role: UserRole = UserRole.PATIENT) -> Appointment:
        async with get_db_session() as session:
            stmt = select(AppointmentModel).where(AppointmentModel.id == appointment_id)
            res = await session.execute(stmt)
            appt = res.scalar_one_or_none()
            if not appt:
                await self.log_audit_async(requester_id, role, "READ_APPOINTMENT", "Appointment", appointment_id, "NOT_FOUND")
                raise AppointmentNotFoundError(f"Appointment {appointment_id} does not exist.")

            if role == UserRole.PATIENT and requester_id != appt.patient_id:
                await self.log_audit_async(requester_id, role, "READ_APPOINTMENT", "Appointment", appointment_id, "DENIED", "RBAC access violation")
                raise EHRError("ACCESS_DENIED", "Access denied: Unauthorized appointment access.")

            await self.log_audit_async(requester_id, role, "READ_APPOINTMENT", "Appointment", appointment_id, "SUCCESS")
            return Appointment(
                id=appt.id,
                patient_id=appt.patient_id,
                provider_id=appt.provider_id,
                procedure_type=appt.procedure_type,
                scheduled_time=appt.scheduled_time,
                status=appt.status,
                location=appt.location,
                notes=appt.notes,
                reschedule_count=appt.reschedule_count
            )

    async def get_patient_appointments_async(self, patient_id: str) -> List[Appointment]:
        async with get_db_session() as session:
            stmt = select(AppointmentModel).where(
                and_(
                    AppointmentModel.patient_id == patient_id,
                    AppointmentModel.status.in_(["scheduled", "rescheduled"])
                )
            ).order_by(AppointmentModel.scheduled_time.asc())
            res = await session.execute(stmt)
            appts = res.scalars().all()
            return [
                Appointment(
                    id=a.id,
                    patient_id=a.patient_id,
                    provider_id=a.provider_id,
                    procedure_type=a.procedure_type,
                    scheduled_time=a.scheduled_time,
                    status=a.status,
                    location=a.location,
                    notes=a.notes,
                    reschedule_count=a.reschedule_count
                )
                for a in appts
            ]

    async def search_available_slots_async(
        self,
        procedure_type: str = "colonoscopy",
        provider_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if self.forced_failure == "TIMEOUT":
            raise ApiTimeoutError("EHR slot search timed out.")
        if self.forced_failure == "SLOT_UNAVAILABLE":
            return []

        candidates = [
            {"date": "2026-10-16", "time": "14:00", "provider_id": "PR101", "provider_name": "Dr. Vivek Patel, MD", "slot_id": "SLOT-20261016-1400", "location": "Suite 400 - Endoscopy Suite A"},
            {"date": "2026-10-16", "time": "15:30", "provider_id": "PR101", "provider_name": "Dr. Vivek Patel, MD", "slot_id": "SLOT-20261016-1530", "location": "Suite 400 - Endoscopy Suite A"},
            {"date": "2026-10-19", "time": "09:00", "provider_id": "PR101", "provider_name": "Dr. Vivek Patel, MD", "slot_id": "SLOT-20261019-0900", "location": "Suite 400 - Endoscopy Suite A"},
            {"date": "2026-10-19", "time": "11:00", "provider_id": "PR102", "provider_name": "Dr. Elena Rostova, MD", "slot_id": "SLOT-20261019-1100", "location": "Suite 400 - Endoscopy Suite B"},
            {"date": "2026-10-23", "time": "14:00", "provider_id": "PR102", "provider_name": "Dr. Elena Rostova, MD", "slot_id": "SLOT-20261023-1400", "location": "Suite 400 - Endoscopy Suite B"},
            {"date": "2026-10-26", "time": "10:00", "provider_id": "PR101", "provider_name": "Dr. Vivek Patel, MD", "slot_id": "SLOT-20261026-1000", "location": "Suite 400 - Endoscopy Suite A"},
        ]

        async with get_db_session() as session:
            stmt = select(AppointmentModel.scheduled_time).where(
                AppointmentModel.status.in_(["scheduled", "rescheduled"])
            )
            res = await session.execute(stmt)
            occupied_dt = [t.strftime("%Y-%m-%d %H:%M") for (t,) in res.all()]

        available = []
        for slot in candidates:
            slot_dt_str = f"{slot['date']} {slot['time']}"
            if slot_dt_str in occupied_dt:
                continue
            if provider_id and slot["provider_id"] != provider_id:
                continue
            if start_date and slot["date"] < start_date:
                continue
            if end_date and slot["date"] > end_date:
                continue
            available.append(slot)

        return available

    async def book_appointment_async(
        self,
        patient_id: str,
        procedure_type: str,
        slot_datetime_str: str,
        provider_id: str = "PR101",
        notes: Optional[str] = None
    ) -> Appointment:
        if self.forced_failure == "TIMEOUT":
            raise ApiTimeoutError("EHR timeout during booking.")
        if self.forced_failure == "SLOT_UNAVAILABLE":
            raise SlotUnavailableError("Slot unavailable due to simulated booking contention.")

        # Parse datetime
        try:
            slot_dt = datetime.strptime(slot_datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                slot_dt = datetime.fromisoformat(slot_datetime_str)
            except ValueError:
                raise EHRError("INVALID_DATETIME", f"Invalid datetime format: {slot_datetime_str}")

        if slot_dt.tzinfo is None:
            slot_dt = slot_dt.replace(tzinfo=timezone.utc)

        appt_id = f"APT-{uuid.uuid4().hex[:6].upper()}"

        async with get_db_session() as session:
            # Check slot collision
            stmt = select(AppointmentModel).where(
                and_(
                    AppointmentModel.scheduled_time == slot_dt,
                    AppointmentModel.status.in_(["scheduled", "rescheduled"])
                )
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                raise SlotUnavailableError(f"Slot {slot_datetime_str} is already booked.")

            new_appt = AppointmentModel(
                id=appt_id,
                patient_id=patient_id,
                provider_id=provider_id,
                procedure_type=procedure_type,
                scheduled_time=slot_dt,
                status="scheduled",
                location="Main Endoscopy Suite - Room 3",
                notes=notes,
                reschedule_count=0
            )
            session.add(new_appt)

            # Audit event
            audit = AuditEventModel(
                id=f"AUD-{uuid.uuid4().hex[:8]}",
                user_id="PATIENT_AGENT",
                event_type="BOOK_APPOINTMENT",
                action="BOOK_APPOINTMENT",
                resource=f"Appointment/{appt_id}",
                patient_id=patient_id,
                details={"slot": slot_datetime_str, "provider": provider_id, "notes": notes}
            )
            session.add(audit)
            await session.commit()

        return Appointment(
            id=appt_id,
            patient_id=patient_id,
            provider_id=provider_id,
            procedure_type=procedure_type,
            scheduled_time=slot_dt,
            status="scheduled",
            location="Main Endoscopy Suite - Room 3",
            notes=notes,
            reschedule_count=0
        )

    async def reschedule_appointment_async(
        self,
        appointment_id: str,
        new_slot_datetime_str: str,
        reason: str = "Patient request"
    ) -> Appointment:
        if self.forced_failure == "TIMEOUT":
            raise ApiTimeoutError("EHR timeout during reschedule.")
        if self.forced_failure == "SLOT_UNAVAILABLE":
            raise SlotUnavailableError("Target reschedule slot unavailable.")

        try:
            new_dt = datetime.strptime(new_slot_datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                new_dt = datetime.fromisoformat(new_slot_datetime_str)
            except ValueError:
                raise EHRError("INVALID_DATETIME", f"Invalid datetime format: {new_slot_datetime_str}")

        if new_dt.tzinfo is None:
            new_dt = new_dt.replace(tzinfo=timezone.utc)

        async with get_db_session() as session:
            stmt = select(AppointmentModel).where(AppointmentModel.id == appointment_id)
            appt = (await session.execute(stmt)).scalar_one_or_none()
            if not appt:
                raise AppointmentNotFoundError(f"Appointment {appointment_id} not found.")

            appt.scheduled_time = new_dt
            appt.status = "rescheduled"
            appt.reschedule_count += 1
            appt.notes = f"{appt.notes or ''} | Rescheduled to {new_dt}. Reason: {reason}"
            appt.updated_at = datetime.now(timezone.utc)

            audit = AuditEventModel(
                id=f"AUD-{uuid.uuid4().hex[:8]}",
                user_id="PATIENT_AGENT",
                event_type="RESCHEDULE_APPOINTMENT",
                action="RESCHEDULE_APPOINTMENT",
                resource=f"Appointment/{appointment_id}",
                patient_id=appt.patient_id,
                details={"new_slot": new_slot_datetime_str, "reason": reason}
            )
            session.add(audit)
            await session.commit()

            return Appointment(
                id=appt.id,
                patient_id=appt.patient_id,
                provider_id=appt.provider_id,
                procedure_type=appt.procedure_type,
                scheduled_time=appt.scheduled_time,
                status=appt.status,
                location=appt.location,
                notes=appt.notes,
                reschedule_count=appt.reschedule_count
            )

    async def cancel_appointment_async(
        self,
        appointment_id: str,
        reason: str = "Patient requested cancellation"
    ) -> Appointment:
        if self.forced_failure == "TIMEOUT":
            raise ApiTimeoutError("EHR timeout during cancellation.")

        async with get_db_session() as session:
            stmt = select(AppointmentModel).where(AppointmentModel.id == appointment_id)
            appt = (await session.execute(stmt)).scalar_one_or_none()
            if not appt:
                raise AppointmentNotFoundError(f"Appointment {appointment_id} not found.")

            appt.status = "cancelled"
            appt.notes = f"{appt.notes or ''} | Cancelled on {datetime.now(timezone.utc)}. Reason: {reason}"
            appt.updated_at = datetime.now(timezone.utc)

            audit = AuditEventModel(
                id=f"AUD-{uuid.uuid4().hex[:8]}",
                user_id="PATIENT_AGENT",
                event_type="CANCEL_APPOINTMENT",
                action="CANCEL_APPOINTMENT",
                resource=f"Appointment/{appointment_id}",
                patient_id=appt.patient_id,
                details={"reason": reason}
            )
            session.add(audit)
            await session.commit()

            return Appointment(
                id=appt.id,
                patient_id=appt.patient_id,
                provider_id=appt.provider_id,
                procedure_type=appt.procedure_type,
                scheduled_time=appt.scheduled_time,
                status=appt.status,
                location=appt.location,
                notes=appt.notes,
                reschedule_count=appt.reschedule_count
            )

    async def create_human_escalation_async(
        self,
        patient_id: str,
        reason: str,
        urgency_level: str = "ROUTINE",
        clinical_context: Optional[str] = None
    ) -> Dict[str, Any]:
        esc_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        payload = {
            "escalation_id": esc_id,
            "patient_id": patient_id,
            "reason": reason,
            "urgency_level": urgency_level,
            "clinical_context": clinical_context,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN"
        }

        async with get_db_session() as session:
            audit = AuditEventModel(
                id=f"AUD-{uuid.uuid4().hex[:8]}",
                user_id="PATIENT_AGENT",
                event_type="HUMAN_ESCALATION_CREATED",
                action="CREATE_HUMAN_ESCALATION",
                resource=f"Escalation/{esc_id}",
                patient_id=patient_id,
                details=payload
            )
            session.add(audit)
            await session.commit()

        return payload

    async def get_prep_protocol_async(self, procedure_type: str = "colonoscopy") -> Optional[PrepProtocol]:
        async with get_db_session() as session:
            stmt = select(PrepProtocolModel).where(
                func.lower(PrepProtocolModel.procedure_type) == func.lower(procedure_type)
            )
            res = (await session.execute(stmt)).scalar_one_or_none()
            if not res:
                return None
            return PrepProtocol(
                id=res.id,
                procedure_type=res.procedure_type,
                title=res.name,
                bowel_prep_type="split_dose_peg",
                diet_rules=[
                    {"days_before": 3, "allowed": ["Low fiber", "White bread", "Eggs", "Poultry"], "prohibited": ["Seeds", "Nuts", "Popcorn", "Raw vegetables"]},
                    {"days_before": 1, "allowed": ["Clear broth", "Apple juice", "Water", "Jell-O (no red/purple)"], "prohibited": ["All solid food", "Dairy", "Red/purple liquids"]}
                ],
                clear_liquids_start_hours_prior=res.clear_liquids_hours,
                split_dose_timing={
                    "first_dose_hours_prior": res.first_dose_hours,
                    "second_dose_hours_prior": res.second_dose_hours,
                    "finish_hours_prior_to_sedation": 2
                },
                medication_adjustments=[
                    {"medication_class": "GLP-1 receptor agonists (Ozempic, Wegovy)", "instruction": "Hold weekly dose 7 days prior to procedure due to delayed gastric emptying aspiration risk."},
                    {"medication_class": "Anticoagulants / Blood Thinners", "instruction": "Consult prescribing cardiologist/physician. Triage team manages bridging."},
                    {"medication_class": "Insulin / Oral Hypoglycemics", "instruction": "Take half dose of basal insulin night before; hold morning insulin day of exam."}
                ],
                red_flags=[
                    "Severe abdominal pain or signs of perforation",
                    "Persistent vomiting preventing prep retention",
                    "Rectal bleeding with dizziness or hemodynamic instability"
                ]
            )

    async def log_audit_async(
        self,
        user_id: str,
        role: UserRole,
        action: str,
        resource_type: str,
        resource_id: str,
        result: str = "SUCCESS",
        details: Optional[str] = None
    ) -> AuditEvent:
        evt_id = f"AUD-{uuid.uuid4().hex[:8]}"
        async with get_db_session() as session:
            db_event = AuditEventModel(
                id=evt_id,
                user_id=user_id,
                event_type=action,
                action=action,
                resource=f"{resource_type}/{resource_id}",
                details={"result": result, "role": role.value if hasattr(role, "value") else str(role), "details": details}
            )
            session.add(db_event)
            await session.commit()

        return AuditEvent(
            id=evt_id,
            user_id=user_id,
            role=role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.now(timezone.utc),
            result=result,
            details=details
        )

    async def reset_state_async(self):
        """Fast reset of appointments and runtime state to baseline for test isolation."""
        self.forced_failure = None
        async with get_db_session() as session:
            # Delete any runtime booked appointments
            await session.execute(
                delete(AppointmentModel).where(
                    and_(
                        AppointmentModel.id != "APT-1001",
                        AppointmentModel.id != "APT-1002",
                        ~AppointmentModel.id.like("SLOT-%")
                    )
                )
            )
            # Restore APT-1001
            appt1 = await session.get(AppointmentModel, "APT-1001")
            if appt1:
                appt1.scheduled_time = datetime(2026, 10, 15, 10, 0, 0)
                appt1.status = "scheduled"
                appt1.reschedule_count = 0
            # Restore APT-1002
            appt2 = await session.get(AppointmentModel, "APT-1002")
            if appt2:
                appt2.scheduled_time = datetime(2026, 10, 22, 8, 30, 0)
                appt2.status = "scheduled"
                appt2.reschedule_count = 0
            await session.commit()

    def reset_state(self):
        return run_async(self.reset_state_async())

    async def take_snapshot_async(self) -> Dict[str, Any]:

        """Query database for current ground truth state of appointments and audit events."""
        async with get_db_session() as session:
            appts = (await session.execute(select(AppointmentModel))).scalars().all()
            audits = (await session.execute(
                select(AuditEventModel).order_by(AuditEventModel.timestamp.desc()).limit(20)
            )).scalars().all()

        appts_dict = {}
        for a in appts:
            appts_dict[a.id] = {
                "id": a.id,
                "patient_id": a.patient_id,
                "provider_id": a.provider_id,
                "procedure_type": a.procedure_type,
                "scheduled_time": a.scheduled_time.isoformat() if hasattr(a.scheduled_time, "isoformat") else str(a.scheduled_time),
                "status": a.status,
                "location": a.location,
                "notes": a.notes,
                "reschedule_count": a.reschedule_count
            }

        events_list = []
        for e in reversed(audits):
            events_list.append({
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
                "event_type": e.event_type,
                "action": e.action,
                "resource": e.resource,
                "patient_id": e.patient_id,
                "payload": e.details or {}
            })

        return {
            "appointments": appts_dict,
            "workflow_events": events_list,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ==================== Synchronous Compatibility Wrappers ====================

    def get_patient(self, patient_id: str, requester_id: str = "P101", role: UserRole = UserRole.PATIENT) -> Patient:
        return run_async(self.get_patient_async(patient_id, requester_id, role))

    def get_appointment(self, appointment_id: str, requester_id: str = "P101", role: UserRole = UserRole.PATIENT) -> Appointment:
        return run_async(self.get_appointment_async(appointment_id, requester_id, role))

    def get_patient_appointments(self, patient_id: str) -> List[Appointment]:
        return run_async(self.get_patient_appointments_async(patient_id))

    def search_available_slots(self, procedure_type: str = "colonoscopy", provider_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        return run_async(self.search_available_slots_async(procedure_type, provider_id, start_date, end_date))

    def book_appointment(self, patient_id: str, procedure_type: str, slot_datetime_str: str, provider_id: str = "PR101", notes: Optional[str] = None) -> Appointment:
        return run_async(self.book_appointment_async(patient_id, procedure_type, slot_datetime_str, provider_id, notes))

    def reschedule_appointment(self, appointment_id: str, new_slot_datetime_str: str, reason: str = "Patient request") -> Appointment:
        return run_async(self.reschedule_appointment_async(appointment_id, new_slot_datetime_str, reason))

    def cancel_appointment(self, appointment_id: str, reason: str = "Patient requested cancellation") -> Appointment:
        return run_async(self.cancel_appointment_async(appointment_id, reason))

    def create_human_escalation(self, patient_id: str, reason: str, urgency_level: str = "ROUTINE", clinical_context: Optional[str] = None) -> Dict[str, Any]:
        return run_async(self.create_human_escalation_async(patient_id, reason, urgency_level, clinical_context))

    def get_prep_protocol(self, procedure_type: str = "colonoscopy") -> Optional[PrepProtocol]:
        return run_async(self.get_prep_protocol_async(procedure_type))

    def take_snapshot(self) -> Dict[str, Any]:
        return run_async(self.take_snapshot_async())

    def diff_snapshot(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Compute deterministic differences between two database state snapshots."""
        diff = {
            "new_appointments": [],
            "modified_appointments": [],
            "cancelled_appointments": [],
            "new_events": []
        }

        before_appts = before.get("appointments", {})
        after_appts = after.get("appointments", {})

        for aid, a_appt in after_appts.items():
            if aid not in before_appts:
                diff["new_appointments"].append(a_appt)
            else:
                b_appt = before_appts[aid]
                if a_appt["status"] != b_appt["status"] or str(a_appt["scheduled_time"]) != str(b_appt["scheduled_time"]):
                    diff["modified_appointments"].append({
                        "id": aid,
                        "before_status": b_appt["status"],
                        "after_status": a_appt["status"],
                        "before_time": str(b_appt["scheduled_time"]),
                        "after_time": str(a_appt["scheduled_time"]),
                        "notes": a_appt.get("notes")
                    })

        before_events_count = len(before.get("workflow_events", []))
        after_events = after.get("workflow_events", [])
        if len(after_events) > before_events_count:
            diff["new_events"] = after_events[before_events_count:]

        return diff


# Global Database-Backed EHR Service instance
ehr_service = EHRService()
