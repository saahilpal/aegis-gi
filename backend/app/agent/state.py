from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from ..models.chat import Citation, TraceStep
from ..models.outcome import AgentClaim
from .safety import SafetyCheckResult

class AgentState(TypedDict, total=False):
    # Core conversation state
    messages: List[Dict[str, str]]
    user_message: str
    patient_id: str
    user_role: str
    
    # Workflow classification & decisions
    request_category: str  # BOOKING, RESCHEDULE, CANCELLATION, PREP_QUESTION, SAFETY_EMERGENCY, OUT_OF_SCOPE, GENERAL
    decision: str  # ANSWER, TAKE_ACTION, ESCALATE
    
    # RAG Context
    retrieved_context: str
    citations: List[Citation]
    retrieval_confidence: float
    is_low_confidence: bool
    
    # Clinical Safety
    safety_result: Optional[SafetyCheckResult]
    
    # Tool Execution
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # Agent Claims & Final Output
    agent_claim: Optional[AgentClaim]
    final_response: str
    
    # Observability & Trace
    trace_steps: List[TraceStep]
    
    # Simulation injection flags for demo & testing
    force_tool_failure: Optional[str]
    force_agent_hallucination: bool
