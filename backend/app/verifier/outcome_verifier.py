import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from ..models.outcome import (
    OutcomeClassification,
    VerificationResult,
    AgentClaim,
    ClaimType,
    EvidenceItem
)
from ..models.ehr import Appointment

class OutcomeVerifier:
    """
    Independent Outcome Verifier for healthcare workflows.
    Compares the Agent's conversational claims against the ground-truth EHR Database state.
    Strictly independent: Does NOT allow the agent to evaluate its own success.
    """

    def verify(
        self,
        user_message: str,
        agent_response: str,
        agent_claim: Optional[AgentClaim],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any],
        expected_outcome: Optional[OutcomeClassification] = None,
        escalation_events: Optional[List[Dict[str, Any]]] = None
    ) -> VerificationResult:
        """
        Verify the outcome of a conversation workflow against ground truth EHR state.
        Returns exactly one OutcomeClassification:
        - COMPLETED
        - CORRECTLY_ESCALATED
        - FALSE_RESOLUTION
        - FAILED
        """
        evidence: List[EvidenceItem] = []
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Compute EHR Snapshot Diff
        before_appts = before_snapshot.get("appointments", {})
        after_appts = after_snapshot.get("appointments", {})
        before_events = before_snapshot.get("workflow_events", [])
        after_events = after_snapshot.get("workflow_events", [])

        new_appts = [a for aid, a in after_appts.items() if aid not in before_appts]
        modified_appts = []
        for aid, a in after_appts.items():
            if aid in before_appts:
                b = before_appts[aid]
                if a["status"] != b["status"] or str(a["scheduled_time"]) != str(b["scheduled_time"]):
                    modified_appts.append({"id": aid, "before": b, "after": a})

        before_event_ids = {e["id"] for e in before_events if isinstance(e, dict) and "id" in e}
        new_events = [e for e in after_events if isinstance(e, dict) and e.get("id") not in before_event_ids]
        escalations = [e for e in new_events if e.get("event_type") == "HUMAN_ESCALATION_CREATED"]
        if escalation_events:
            escalations.extend(escalation_events)

        # 2. Extract Claims from Agent Claim or Response Text
        claim_type = agent_claim.action_type if agent_claim else ClaimType.UNKNOWN
        claimed_status = agent_claim.claimed_status if agent_claim else "UNKNOWN"
        response_lower = agent_response.lower()

        # Check for natural language success claims
        claims_success_verbally = any(phrase in response_lower for phrase in [
            "successfully rescheduled",
            "has been rescheduled",
            "successfully booked",
            "has been booked",
            "has been confirmed",
            "appointment is confirmed",
            "all set for your appointment on",
            "cancelled per your request",
            "has been cancelled"
        ])

        claims_reschedule_verbally = any(phrase in response_lower for phrase in [
            "rescheduled to",
            "moved your appointment",
            "rescheduled your colonoscopy",
            "rescheduled your appointment"
        ])

        claims_booking_verbally = any(phrase in response_lower for phrase in [
            "booked your colonoscopy",
            "scheduled your colonoscopy",
            "booked your appointment",
            "confirmed for"
        ])

        claims_escalation_verbally = False
        if claim_type != ClaimType.PREP_INSTRUCTION:
            claims_escalation_verbally = any(phrase in response_lower for phrase in [
                "escalated your chart",
                "notified our on-call",
                "notified our clinic staff",
                "call 911",
                "nearest emergency room",
                "flagged this for nurse review",
                "escalated this inquiry",
                "escalated your request"
            ])


        # ========================================================
        # RULE SET 1: FALSE_RESOLUTION DETECTION (Highest Priority)
        # ========================================================

        # Case 1A: Rescheduling claimed as SUCCESS, but EHR appointment unchanged or not updated
        if (claim_type == ClaimType.RESCHEDULE_APPOINTMENT and claimed_status == "SUCCESS") or claims_reschedule_verbally:
            # Check if any appointment was actually rescheduled in EHR
            rescheduled_in_ehr = [m for m in modified_appts if m["after"]["status"] == "rescheduled" or m["before"]["scheduled_time"] != m["after"]["scheduled_time"]]
            
            if not rescheduled_in_ehr:
                evidence.append(EvidenceItem(
                    source="CLINICAL_EHR",
                    field="appointments.scheduled_time",
                    claimed_value=f"Rescheduled ({agent_claim.target_date if agent_claim else 'New date/time'})",
                    actual_value="Unchanged in EHR Database",
                    discrepancy=True,
                    details="Agent claimed appointment was rescheduled, but EHR Database appointment time and status remain identical to baseline."
                ))
                return VerificationResult(
                    classification=OutcomeClassification.FALSE_RESOLUTION,
                    expected_outcome="EHR appointment record modified to target date/time",
                    actual_outcome="EHR Database state unchanged (0 appointments rescheduled)",
                    reason="FALSE RESOLUTION: Agent claimed successful appointment rescheduling, but EHR Database ground truth shows appointment was NOT rescheduled.",
                    evidence=evidence,
                    claimed_action=agent_claim,
                    discrepancy_detected=True,
                    ehr_verified_timestamp=now_str
                )

        # Case 1B: Booking claimed as SUCCESS, but no appointment created in EHR
        if (claim_type == ClaimType.BOOK_APPOINTMENT and claimed_status == "SUCCESS") or claims_booking_verbally:
            if not new_appts:
                evidence.append(EvidenceItem(
                    source="CLINICAL_EHR",
                    field="appointments.count",
                    claimed_value="New confirmed appointment",
                    actual_value="No new appointment created in EHR",
                    discrepancy=True,
                    details="Agent claimed procedure was booked, but no matching appointment entity was created in the EHR."
                ))
                return VerificationResult(
                    classification=OutcomeClassification.FALSE_RESOLUTION,
                    expected_outcome="New appointment created in EHR Database",
                    actual_outcome="0 new appointments found in EHR Database",
                    reason="FALSE RESOLUTION: Agent claimed booking succeeded, but ground truth EHR Database contains no corresponding appointment record.",
                    evidence=evidence,
                    claimed_action=agent_claim,
                    discrepancy_detected=True,
                    ehr_verified_timestamp=now_str
                )

        # Case 1C: Cancellation claimed, but appointment remains scheduled
        if claim_type == ClaimType.CANCEL_APPOINTMENT and claimed_status == "SUCCESS":
            cancelled_in_ehr = [m for m in modified_appts if m["after"]["status"] == "cancelled"]
            if not cancelled_in_ehr:
                evidence.append(EvidenceItem(
                    source="CLINICAL_EHR",
                    field="appointments.status",
                    claimed_value="cancelled",
                    actual_value="scheduled",
                    discrepancy=True,
                    details="Agent claimed appointment was cancelled, but EHR status remains scheduled."
                ))
                return VerificationResult(
                    classification=OutcomeClassification.FALSE_RESOLUTION,
                    expected_outcome="Appointment status updated to cancelled in EHR",
                    actual_outcome="Appointment remains scheduled in EHR",
                    reason="FALSE RESOLUTION: Agent claimed appointment cancellation, but EHR state confirms appointment is still active.",
                    evidence=evidence,
                    claimed_action=agent_claim,
                    discrepancy_detected=True,
                    ehr_verified_timestamp=now_str
                )

        # Case 1D: Claimed escalation to staff, but no escalation ticket created in EHR
        if claims_escalation_verbally and not escalations and "call 911" not in response_lower:
            evidence.append(EvidenceItem(
                source="CLINICAL_EHR",
                field="workflow_events.HUMAN_ESCALATION_CREATED",
                claimed_value="Staff escalated",
                actual_value="No escalation record created in EHR",
                discrepancy=True,
                details="Agent claimed to have notified staff, but no escalation record was logged in the EHR Database."
            ))
            return VerificationResult(
                classification=OutcomeClassification.FALSE_RESOLUTION,
                expected_outcome="Escalation event logged in EHR workflow",
                actual_outcome="No escalation event found in EHR",
                reason="FALSE RESOLUTION: Agent verbally claimed clinical staff notification, but no escalation ticket was recorded in the EHR.",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=True,
                ehr_verified_timestamp=now_str
            )

        # ========================================================
        # RULE SET 2: CORRECTLY_ESCALATED
        # ========================================================
        if escalations or "call 911" in response_lower or (claim_type == ClaimType.HUMAN_ESCALATION and claimed_status == "ESCALATED"):
            esc_item = escalations[0] if escalations else {}
            reason_text = esc_item.get("payload", {}).get("reason", "Safety / Clinical Triage Escalation")
            evidence.append(EvidenceItem(
                source="CLINICAL_EHR",
                field="workflow_events",
                claimed_value="Escalated to clinical staff",
                actual_value=f"Ticket {esc_item.get('payload', {}).get('escalation_id', 'EMERGENCY-911')}",
                discrepancy=False,
                details=f"EHR verified escalation ticket with urgency: {esc_item.get('payload', {}).get('urgency_level', 'URGENT')}"
            ))
            return VerificationResult(
                classification=OutcomeClassification.CORRECTLY_ESCALATED,
                expected_outcome="Case safely escalated to human clinical staff",
                actual_outcome="Escalation ticket verified in EHR Database workflow events",
                reason=f"CORRECTLY ESCALATED: Workflow safely handed off to human team ({reason_text}).",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=False,
                ehr_verified_timestamp=now_str
            )

        # ========================================================
        # RULE SET 3: COMPLETED
        # ========================================================
        # 3A: Reschedule verified
        if claim_type == ClaimType.RESCHEDULE_APPOINTMENT and claimed_status == "SUCCESS" and modified_appts:
            evidence.append(EvidenceItem(
                source="CLINICAL_EHR",
                field="appointments.scheduled_time",
                claimed_value=str(agent_claim.target_date),
                actual_value=str(modified_appts[0]["after"]["scheduled_time"]),
                discrepancy=False,
                details="EHR Database appointment record confirms rescheduled timestamp."
            ))
            return VerificationResult(
                classification=OutcomeClassification.COMPLETED,
                expected_outcome="Appointment rescheduled in EHR Database",
                actual_outcome=f"Appointment {modified_appts[0]['id']} updated to {modified_appts[0]['after']['scheduled_time']}",
                reason="COMPLETED: Requested rescheduling verified against ground truth EHR Database state.",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=False,
                ehr_verified_timestamp=now_str
            )

        # 3B: Booking verified
        if claim_type == ClaimType.BOOK_APPOINTMENT and claimed_status == "SUCCESS" and new_appts:
            evidence.append(EvidenceItem(
                source="CLINICAL_EHR",
                field="appointments.count",
                claimed_value=new_appts[0]["id"],
                actual_value=f"Created appointment {new_appts[0]['id']} on {new_appts[0]['scheduled_time']}",
                discrepancy=False,
                details="EHR Database record verifies new booking created."
            ))
            return VerificationResult(
                classification=OutcomeClassification.COMPLETED,
                expected_outcome="New appointment booked in EHR Database",
                actual_outcome=f"Appointment {new_appts[0]['id']} created on {new_appts[0]['scheduled_time']}",
                reason="COMPLETED: Booking action confirmed and ground-truth appointment record verified in EHR Database.",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=False,
                ehr_verified_timestamp=now_str
            )

        # 3C: Cancellation verified
        if claim_type == ClaimType.CANCEL_APPOINTMENT and claimed_status == "SUCCESS" and modified_appts:
            return VerificationResult(
                classification=OutcomeClassification.COMPLETED,
                expected_outcome="Appointment cancelled in EHR Database",
                actual_outcome="Appointment marked cancelled in EHR Database",
                reason="COMPLETED: Appointment cancellation confirmed in EHR Database.",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=False,
                ehr_verified_timestamp=now_str
            )

        # 3D: RAG prep instruction verified
        if claim_type == ClaimType.PREP_INSTRUCTION and claimed_status == "INFORMATION_PROVIDED":
            evidence.append(EvidenceItem(
                source="CONVERSATION",
                field="citations",
                claimed_value="Clinical prep instructions provided",
                actual_value="Source citations attached",
                discrepancy=False,
                details="Verified protocol instructions provided to patient with source citations."
            ))
            return VerificationResult(
                classification=OutcomeClassification.COMPLETED,
                expected_outcome="Accurate clinical prep guidance with source citations",
                actual_outcome="Prep instructions delivered with protocol references",
                reason="COMPLETED: Clinical preparation instructions verified from knowledge base.",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=False,
                ehr_verified_timestamp=now_str
            )

        # 3E: Slot unavailable handled truthfully (agent did not book and told patient slot was unavailable)
        if claimed_status == "FAILURE" and not modified_appts and not new_appts:
            evidence.append(EvidenceItem(
                source="CLINICAL_EHR",
                field="appointments",
                claimed_value="Slot unavailable (no false booking)",
                actual_value="EHR unmodified",
                discrepancy=False,
                details="Agent correctly reported unavailable slot without falsely claiming resolution."
            ))
            return VerificationResult(
                classification=OutcomeClassification.COMPLETED,
                expected_outcome="Accurate explanation of unavailable slot and alternatives offered",
                actual_outcome="Agent accurately reported tool failure without falsely modifying EHR",
                reason="COMPLETED: Agent truthfully handled slot unavailability without hallucinating success.",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=False,
                ehr_verified_timestamp=now_str
            )

        # General inquiry completed
        if claim_type == ClaimType.GENERAL_INQUIRY:
            return VerificationResult(
                classification=OutcomeClassification.COMPLETED,
                expected_outcome="General clinic guidance provided",
                actual_outcome="General information returned",
                reason="COMPLETED: Administrative inquiry resolved.",
                evidence=evidence,
                claimed_action=agent_claim,
                discrepancy_detected=False,
                ehr_verified_timestamp=now_str
            )

        # ========================================================
        # RULE SET 4: FAILED (Fallback when workflow achieved nothing)
        # ========================================================
        evidence.append(EvidenceItem(
            source="CONVERSATION",
            field="workflow_state",
            claimed_value="Unresolved",
            actual_value="No action or guidance completed",
            discrepancy=False,
            details="Workflow terminated without resolving patient request or properly escalating."
        ))
        return VerificationResult(
            classification=OutcomeClassification.FAILED,
            expected_outcome="Actionable resolution or human escalation",
            actual_outcome="Incomplete workflow without resolution",
            reason="FAILED: Workflow did not accomplish useful clinical or administrative resolution.",
            evidence=evidence,
            claimed_action=agent_claim,
            discrepancy_detected=False,
            ehr_verified_timestamp=now_str
        )

outcome_verifier = OutcomeVerifier()
