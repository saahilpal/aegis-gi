import pytest
import asyncio
from datetime import datetime
from backend.app.ehr.ehr_service import ehr_service
from backend.app.verifier.outcome_verifier import outcome_verifier
from backend.app.models.outcome import OutcomeClassification, AgentClaim, ClaimType
from backend.app.db.seed import seed_database

@pytest.fixture(autouse=True)
def reset_db():
    asyncio.run(seed_database())

def test_outcome_verifier_detects_false_resolution():
    """Verify that when an agent claims rescheduling succeeded but EHR is unchanged, FALSE_RESOLUTION is flagged."""
    before_snap = ehr_service.take_snapshot()
    # EHR is NOT modified
    after_snap = ehr_service.take_snapshot()

    claim = AgentClaim(
        action_type=ClaimType.RESCHEDULE_APPOINTMENT,
        claimed_status="SUCCESS",
        statement="Your appointment has been rescheduled to Friday at 3 PM.",
        target_date="2026-10-16",
        target_time="15:00"
    )

    ver = outcome_verifier.verify(
        user_message="Reschedule my appointment to Friday at 3 PM",
        agent_response="Your appointment has been rescheduled to Friday at 3 PM.",
        agent_claim=claim,
        before_snapshot=before_snap,
        after_snapshot=after_snap
    )

    assert ver.classification == OutcomeClassification.FALSE_RESOLUTION
    assert ver.discrepancy_detected is True
    assert "FALSE RESOLUTION" in ver.reason

def test_outcome_verifier_verifies_completed():
    """Verify that when an agent claims rescheduling and EHR is actually updated, COMPLETED is returned."""
    before_snap = ehr_service.take_snapshot()
    
    # Actually perform reschedule in EHR
    ehr_service.reschedule_appointment("APT-1001", "2026-10-16 14:00")
    after_snap = ehr_service.take_snapshot()

    claim = AgentClaim(
        action_type=ClaimType.RESCHEDULE_APPOINTMENT,
        claimed_status="SUCCESS",
        statement="Your appointment has been rescheduled to 2026-10-16 14:00.",
        target_date="2026-10-16",
        target_time="14:00"
    )

    ver = outcome_verifier.verify(
        user_message="Reschedule my appointment to Friday",
        agent_response="Your appointment has been rescheduled to 2026-10-16 14:00.",
        agent_claim=claim,
        before_snapshot=before_snap,
        after_snapshot=after_snap
    )

    assert ver.classification == OutcomeClassification.COMPLETED
    assert ver.discrepancy_detected is False

def test_outcome_verifier_correctly_escalated():
    """Verify that safety red-flag escalation creates verified ticket and classifies as CORRECTLY_ESCALATED."""
    before_snap = ehr_service.take_snapshot()

    # Log escalation ticket in EHR
    ehr_service.create_human_escalation("P101", "Suspected GI bleeding emergency", "EMERGENCY_911")
    after_snap = ehr_service.take_snapshot()

    claim = AgentClaim(
        action_type=ClaimType.HUMAN_ESCALATION,
        claimed_status="ESCALATED",
        statement="Please call 911 immediately. I have escalated this emergency to clinical staff."
    )

    ver = outcome_verifier.verify(
        user_message="I have severe bleeding with blood clots in the toilet",
        agent_response="Please call 911 immediately.",
        agent_claim=claim,
        before_snapshot=before_snap,
        after_snapshot=after_snap
    )

    assert ver.classification == OutcomeClassification.CORRECTLY_ESCALATED
    assert ver.discrepancy_detected is False
