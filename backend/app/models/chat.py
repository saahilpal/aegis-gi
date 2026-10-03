import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from .outcome import VerificationResult, AgentClaim
from .audit import UserRole

class Citation(BaseModel):
    source_document: str
    source_section: str
    text_snippet: str
    confidence: float = 1.0

class TraceStep(BaseModel):
    node_id: str
    node_name: str
    status: str = "COMPLETED"  # "COMPLETED", "SKIPPED", "FAILED", "RUNNING"
    latency_ms: float = 0.0
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    citations: List[Citation] = Field(default_factory=list)
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="Patient message text (1-4000 chars)")
    conversation_id: Optional[str] = Field(None, max_length=64)
    patient_id: str = Field("P101", min_length=2, max_length=64)
    user_role: UserRole = UserRole.PATIENT
    # Simulation flags for demonstration & testing
    force_tool_failure: Optional[str] = Field(None, max_length=32)
    force_agent_hallucination: bool = False

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty or purely whitespace.")
        # Reject null bytes
        if "\x00" in cleaned:
            raise ValueError("Null bytes are not allowed in messages.")
        # Disarm active script tags (prevent stored/reflected XSS)
        cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "[SCRUBBED_SCRIPT]", cleaned, flags=re.IGNORECASE | re.DOTALL)
        return cleaned

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, v: str) -> str:
        cleaned = v.strip()
        if not re.match(r"^[A-Za-z0-9_-]{2,64}$", cleaned):
            raise ValueError("Invalid patient_id format. Must be alphanumeric with hyphens/underscores.")
        return cleaned

class ChatResponse(BaseModel):
    conversation_id: str
    response_text: str
    citations: List[Citation] = Field(default_factory=list)
    claimed_action: Optional[AgentClaim] = None
    outcome_verification: VerificationResult
    trace_steps: List[TraceStep] = Field(default_factory=list)
    ehr_snapshot: Optional[Dict[str, Any]] = None
    total_latency_ms: float = 0.0

class StreamChunk(BaseModel):
    event: str  # "token", "trace", "claim", "ehr_diff", "outcome", "done", "error"
    data: Dict[str, Any]
