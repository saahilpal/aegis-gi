import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.db.seed import seed_database
from backend.app.models.chat import ChatRequest
from backend.app.security.rate_limiter import InMemoryRateLimiter
from backend.app.security.idempotency import IdempotencyCache
from backend.app.ehr.ehr_service import ehr_service, SlotUnavailableError, EHRError
from backend.app.models.audit import UserRole
from backend.app.rag.retriever import retrieve_prep_context
from backend.app.routers.auth_router import create_access_token

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db_fixture():
    asyncio.run(seed_database(force=True))

def get_auth_header(sub: str, role: str, patient_id: str = None) -> dict:
    claims = {"sub": sub, "role": role}
    if patient_id:
        claims["patient_id"] = patient_id
    token = create_access_token(claims)
    return {"Authorization": f"Bearer {token}"}

# 1. Cross-patient authorization enforcement (IDOR prevention)
def test_unauthorized_cross_patient_access():
    headers = get_auth_header(sub="P101", role=UserRole.PATIENT.value, patient_id="P101")
    resp = client.get("/api/ehr/patients/P102", headers=headers)
    assert resp.status_code == 403
    assert "Access Denied" in resp.json().get("detail", "")

# 2. Patient role cannot reset database
def test_patient_cannot_reset_database():
    headers = get_auth_header(sub="P101", role=UserRole.PATIENT.value, patient_id="P101")
    resp = client.post("/api/ehr/reset", headers=headers)
    assert resp.status_code == 403
    assert "Access Denied: Patients cannot execute destructive EHR database resets" in resp.json().get("detail", "")

# 3. Patient role cannot trigger benchmark evaluations
def test_patient_cannot_run_eval():
    headers = get_auth_header(sub="P101", role=UserRole.PATIENT.value, patient_id="P101")
    resp = client.post("/api/eval/run", headers=headers)
    assert resp.status_code == 403
    assert "Access Denied: Patients cannot trigger evaluation suites" in resp.json().get("detail", "")

# 4. Message length limit (max 4000 characters)
def test_message_length_boundary_validation():
    with pytest.raises(ValidationError):
        ChatRequest(
            message="A" * 4001,
            patient_id="P101"
        )

# 5. Empty or whitespace-only message rejected
def test_empty_message_validation():
    with pytest.raises(ValidationError):
        ChatRequest(
            message="   ",
            patient_id="P101"
        )

# 6. Input sanitization strips script tags and rejects null bytes
def test_input_sanitization():
    req = ChatRequest(
        message="Hello <script>alert('pwn')</script> doctor",
        patient_id="P101"
    )
    assert "<script>" not in req.message
    assert "</script>" not in req.message
    assert "[SCRUBBED_SCRIPT]" in req.message

    with pytest.raises(ValidationError):
        ChatRequest(
            message="Null byte \x00 attack",
            patient_id="P101"
        )

# 7. Rescheduling to a past date is rejected
def test_reschedule_to_past_date_rejected():
    headers = get_auth_header(sub="P101", role=UserRole.PATIENT.value, patient_id="P101")
    payload = {
        "new_slot_datetime": "2020-01-01T10:00:00Z",
        "reason": "Invalid past date request"
    }
    resp = client.patch("/api/ehr/appointments/APT-1001", json=payload, headers=headers)
    assert resp.status_code == 422
    assert "in the past" in str(resp.json())

# 8. Double booking prevention (race condition simulation)
def test_double_booking_prevention():
    slots = ehr_service.search_available_slots("colonoscopy")
    assert len(slots) > 0
    slot = slots[0]
    slot_dt = f"{slot['date']} {slot['time']}"

    # First booking succeeds
    appt1 = ehr_service.book_appointment(
        patient_id="P101",
        procedure_type="colonoscopy",
        slot_datetime_str=slot_dt,
        provider_id=slot["provider_id"]
    )
    assert appt1.id.startswith("APT-")

    # Second booking for the exact same slot raises SlotUnavailableError
    with pytest.raises(SlotUnavailableError):
        ehr_service.book_appointment(
            patient_id="P102",
            procedure_type="colonoscopy",
            slot_datetime_str=slot_dt,
            provider_id=slot["provider_id"]
        )

# 9. Idempotency cache prevents duplicated mutations
def test_idempotency_cache():
    cache = IdempotencyCache(ttl_seconds=60)
    key = "idem-test-key-123"
    
    assert cache.get(key) is None
    cached_payload = {"status": "success", "appointment_id": "APT-9999"}
    cache.set(key, cached_payload)
    
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved["result"] == cached_payload

# 10. Rate limiter sliding-window enforcement
def test_rate_limiter_sliding_window():
    limiter = InMemoryRateLimiter()
    client_ip = "192.168.1.50"
    
    allowed1, _ = limiter.check(client_ip, max_requests=3, window_seconds=10)
    allowed2, _ = limiter.check(client_ip, max_requests=3, window_seconds=10)
    allowed3, _ = limiter.check(client_ip, max_requests=3, window_seconds=10)
    allowed4, retry_after = limiter.check(client_ip, max_requests=3, window_seconds=10)
    
    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is True
    assert allowed4 is False
    assert retry_after > 0

# 11. Zero RAG retrieval returns low confidence without hallucinated citations
def test_rag_zero_results_low_confidence():
    result = retrieve_prep_context("quantum tunneling superconducting plasma flux")
    # Low confidence result should not fabricate citations
    assert result.is_low_confidence is True
    assert len(result.citations) == 0
