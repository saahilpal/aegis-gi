import pytest
import asyncio
from backend.app.ehr.ehr_service import (
    ehr_service,
    SlotUnavailableError,
    AppointmentNotFoundError,
    ApiTimeoutError,
    EHRError
)
from backend.app.models.audit import UserRole
from backend.app.db.seed import seed_database

@pytest.fixture(autouse=True)
def reset_db():
    asyncio.run(seed_database())

def test_ehr_patient_retrieval_and_rbac():
    # Self-access
    p = ehr_service.get_patient("P101", requester_id="P101", role=UserRole.PATIENT)
    assert p.first_name == "Sarah"

    # Patient accessing another patient's chart must be blocked
    with pytest.raises(EHRError) as exc:
        ehr_service.get_patient("P102", requester_id="P101", role=UserRole.PATIENT)
    assert exc.value.code == "ACCESS_DENIED"

def test_ehr_booking_and_slot_search():
    slots = ehr_service.search_available_slots("colonoscopy")
    assert len(slots) > 0

    first_slot = slots[0]
    target_dt = f"{first_slot['date']} {first_slot['time']}"
    
    # Book appointment
    new_appt = ehr_service.book_appointment(
        patient_id="P101",
        procedure_type="colonoscopy",
        slot_datetime_str=target_dt,
        provider_id=first_slot["provider_id"]
    )
    assert new_appt.id.startswith("APT-")
    assert new_appt.status == "scheduled"

    # Booking the same slot again should fail with SlotUnavailableError
    with pytest.raises(SlotUnavailableError):
        ehr_service.book_appointment(
            patient_id="P101",
            procedure_type="colonoscopy",
            slot_datetime_str=target_dt,
            provider_id=first_slot["provider_id"]
        )

def test_ehr_reschedule_and_cancel():
    # Reschedule Sarah's existing appointment
    updated = ehr_service.reschedule_appointment("APT-1001", "2026-10-19 09:00", reason="Patient preference")
    assert updated.status == "rescheduled"
    assert "2026-10-19 09:00" in str(updated.scheduled_time)

    # Cancel appointment
    cancelled = ehr_service.cancel_appointment("APT-1001", reason="Testing cancellation")
    assert cancelled.status == "cancelled"

def test_ehr_fault_injection():
    ehr_service.forced_failure = "TIMEOUT"
    with pytest.raises(ApiTimeoutError):
        ehr_service.search_available_slots()
    ehr_service.forced_failure = None
