from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
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
    message: str
    conversation_id: Optional[str] = None
    patient_id: str = "P101"
    user_role: UserRole = UserRole.PATIENT
    # Simulation flags for demonstration & testing
    force_tool_failure: Optional[str] = None  # e.g., "SLOT_UNAVAILABLE", "TIMEOUT", "NONE"
    force_agent_hallucination: bool = False  # e.g., force agent to claim success despite failure

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
