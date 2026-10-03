from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class OutcomeClassification(str, Enum):
    COMPLETED = "COMPLETED"
    CORRECTLY_ESCALATED = "CORRECTLY_ESCALATED"
    FALSE_RESOLUTION = "FALSE_RESOLUTION"
    FAILED = "FAILED"

class ClaimType(str, Enum):
    BOOK_APPOINTMENT = "BOOK_APPOINTMENT"
    RESCHEDULE_APPOINTMENT = "RESCHEDULE_APPOINTMENT"
    CANCEL_APPOINTMENT = "CANCEL_APPOINTMENT"
    PREP_INSTRUCTION = "PREP_INSTRUCTION"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    UNKNOWN = "UNKNOWN"

class AgentClaim(BaseModel):
    action_type: ClaimType
    claimed_status: str  # "SUCCESS", "FAILURE", "ESCALATED", "INFORMATION_PROVIDED"
    statement: str
    target_date: Optional[str] = None
    target_time: Optional[str] = None
    appointment_id: Optional[str] = None
    patient_id: Optional[str] = None
    confidence: float = 1.0

class EvidenceItem(BaseModel):
    source: str  # "CLINICAL_EHR", "CONVERSATION", "TOOL_TRACE", "AUDIT_LOG"
    field: str
    claimed_value: Optional[str] = None
    actual_value: Optional[str] = None
    discrepancy: bool = False
    details: str

class VerificationResult(BaseModel):
    classification: OutcomeClassification
    expected_outcome: str
    actual_outcome: str
    reason: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    claimed_action: Optional[AgentClaim] = None
    discrepancy_detected: bool = False
    ehr_verified_timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
