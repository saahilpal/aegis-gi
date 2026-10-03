from typing import Optional, Dict, Any, List
from ..ehr.ehr_service import (
    ehr_service,
    EHRError,
    SlotUnavailableError,
    AppointmentNotFoundError,
    ApiTimeoutError,
    ConflictingAppointmentError,
    MissingPatientInfoError
)
from ..rag.retriever import retrieve_prep_context

def search_available_slots(procedure_type: str = "colonoscopy", provider_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Search EHR database for open procedure time slots.
    """
    try:
        slots = ehr_service.search_available_slots(procedure_type, provider_id, start_date, end_date)
        return {
            "status": "SUCCESS",
            "slots": slots,
            "count": len(slots),
            "message": f"Found {len(slots)} available slots for {procedure_type}."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message,
            "slots": []
        }

async def search_available_slots_async(procedure_type: str = "colonoscopy", provider_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    try:
        slots = await ehr_service.search_available_slots_async(procedure_type, provider_id, start_date, end_date)
        return {
            "status": "SUCCESS",
            "slots": slots,
            "count": len(slots),
            "message": f"Found {len(slots)} available slots for {procedure_type}."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message,
            "slots": []
        }

def book_appointment(patient_id: str, procedure_type: str, slot_datetime: str, provider_id: str = "PR101", notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Book a procedure appointment in the EHR database.
    """
    try:
        appt = ehr_service.book_appointment(patient_id, procedure_type, slot_datetime, provider_id, notes)
        return {
            "status": "SUCCESS",
            "appointment_id": appt.id,
            "scheduled_time": appt.scheduled_time.isoformat() if hasattr(appt.scheduled_time, "isoformat") else str(appt.scheduled_time),
            "patient_id": appt.patient_id,
            "provider_id": appt.provider_id,
            "procedure_type": appt.procedure_type,
            "location": appt.location,
            "message": f"Successfully confirmed booking for {appt.procedure_type} on {appt.scheduled_time}."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message
        }

async def book_appointment_async(patient_id: str, procedure_type: str, slot_datetime: str, provider_id: str = "PR101", notes: Optional[str] = None) -> Dict[str, Any]:
    try:
        appt = await ehr_service.book_appointment_async(patient_id, procedure_type, slot_datetime, provider_id, notes)
        return {
            "status": "SUCCESS",
            "appointment_id": appt.id,
            "scheduled_time": appt.scheduled_time.isoformat() if hasattr(appt.scheduled_time, "isoformat") else str(appt.scheduled_time),
            "patient_id": appt.patient_id,
            "provider_id": appt.provider_id,
            "procedure_type": appt.procedure_type,
            "location": appt.location,
            "message": f"Successfully confirmed booking for {appt.procedure_type} on {appt.scheduled_time}."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message
        }

def reschedule_appointment(appointment_id: str, new_slot_datetime: str, reason: str = "Patient request") -> Dict[str, Any]:
    """
    Reschedule an existing appointment in EHR database.
    """
    try:
        appt = ehr_service.reschedule_appointment(appointment_id, new_slot_datetime, reason)
        return {
            "status": "SUCCESS",
            "appointment_id": appt.id,
            "new_scheduled_time": appt.scheduled_time.isoformat() if hasattr(appt.scheduled_time, "isoformat") else str(appt.scheduled_time),
            "status_in_ehr": appt.status,
            "message": f"Successfully rescheduled appointment {appointment_id} to {appt.scheduled_time}."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message
        }

async def reschedule_appointment_async(appointment_id: str, new_slot_datetime: str, reason: str = "Patient request") -> Dict[str, Any]:
    try:
        appt = await ehr_service.reschedule_appointment_async(appointment_id, new_slot_datetime, reason)
        return {
            "status": "SUCCESS",
            "appointment_id": appt.id,
            "new_scheduled_time": appt.scheduled_time.isoformat() if hasattr(appt.scheduled_time, "isoformat") else str(appt.scheduled_time),
            "status_in_ehr": appt.status,
            "message": f"Successfully rescheduled appointment {appointment_id} to {appt.scheduled_time}."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message
        }

def cancel_appointment(appointment_id: str, reason: str = "Patient requested cancellation") -> Dict[str, Any]:
    """
    Cancel an existing appointment in EHR database.
    """
    try:
        appt = ehr_service.cancel_appointment(appointment_id, reason)
        return {
            "status": "SUCCESS",
            "appointment_id": appt.id,
            "status_in_ehr": appt.status,
            "message": f"Appointment {appointment_id} has been cancelled."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message
        }

async def cancel_appointment_async(appointment_id: str, reason: str = "Patient requested cancellation") -> Dict[str, Any]:
    try:
        appt = await ehr_service.cancel_appointment_async(appointment_id, reason)
        return {
            "status": "SUCCESS",
            "appointment_id": appt.id,
            "status_in_ehr": appt.status,
            "message": f"Appointment {appointment_id} has been cancelled."
        }
    except EHRError as e:
        return {
            "status": "ERROR",
            "error_code": e.code,
            "message": e.message
        }

def get_patient_appointment(patient_id: str, appointment_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve upcoming appointments for a patient.
    """
    try:
        if appointment_id:
            appt = ehr_service.get_appointment(appointment_id)
            return {"status": "SUCCESS", "appointment": appt.dict()}
        
        appts = ehr_service.get_patient_appointments(patient_id)
        if not appts:
            return {"status": "SUCCESS", "appointments": [], "message": f"No active appointments found for patient {patient_id}."}
        return {"status": "SUCCESS", "appointments": [a.dict() for a in appts]}
    except EHRError as e:
        return {"status": "ERROR", "error_code": e.code, "message": e.message}

async def get_patient_appointment_async(patient_id: str, appointment_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        if appointment_id:
            appt = await ehr_service.get_appointment_async(appointment_id)
            return {"status": "SUCCESS", "appointment": appt.dict()}
        
        appts = await ehr_service.get_patient_appointments_async(patient_id)
        if not appts:
            return {"status": "SUCCESS", "appointments": [], "message": f"No active appointments found for patient {patient_id}."}
        return {"status": "SUCCESS", "appointments": [a.dict() for a in appts]}
    except EHRError as e:
        return {"status": "ERROR", "error_code": e.code, "message": e.message}

def get_procedure(procedure_id: str = "PROC-COLON") -> Dict[str, Any]:
    """
    Look up clinical procedure details.
    """
    return {
        "status": "SUCCESS",
        "procedure": {
            "id": procedure_id,
            "code": "45378",
            "name": "Diagnostic Colonoscopy with Possible Polypectomy",
            "default_duration_minutes": 60,
            "requires_prep": True,
            "requires_sedation": True,
            "description": "Endoscopic visual examination of the large bowel and distal ileum."
        }
    }

def search_prep_protocol(procedure_type: str = "colonoscopy", query: str = "") -> Dict[str, Any]:
    """
    Search clinical prep protocols with semantic RAG retriever.
    """
    res = retrieve_prep_context(query)
    return {
        "status": "SUCCESS",
        "content": res.content,
        "citations": [c.dict() for c in res.citations],
        "confidence": res.confidence,
        "is_low_confidence": res.is_low_confidence
    }

def create_human_escalation(patient_id: str, reason: str, urgency_level: str = "ROUTINE", clinical_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a verified human escalation record in EHR database.
    """
    ticket = ehr_service.create_human_escalation(patient_id, reason, urgency_level, clinical_context)
    return {
        "status": "SUCCESS",
        "escalation_ticket": ticket,
        "message": f"Escalation ticket {ticket['escalation_id']} created. Urgency: {urgency_level}."
    }

async def create_human_escalation_async(patient_id: str, reason: str, urgency_level: str = "ROUTINE", clinical_context: Optional[str] = None) -> Dict[str, Any]:
    ticket = await ehr_service.create_human_escalation_async(patient_id, reason, urgency_level, clinical_context)
    return {
        "status": "SUCCESS",
        "escalation_ticket": ticket,
        "message": f"Escalation ticket {ticket['escalation_id']} created. Urgency: {urgency_level}."
    }

