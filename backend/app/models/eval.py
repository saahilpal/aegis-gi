from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from .outcome import OutcomeClassification

class EvalScenario(BaseModel):
    id: str
    category: str
    name: str
    patient_id: str = "P101"
    user_input: str
    expected_outcome: OutcomeClassification
    expected_action: Optional[str] = None
    simulate_tool_failure: Optional[str] = None  # e.g., "SLOT_UNAVAILABLE", "TIMEOUT", "NONE"
    simulate_agent_hallucination: bool = False
    notes: Optional[str] = None

class ScenarioResult(BaseModel):
    scenario_id: str
    category: str
    name: str
    user_input: str
    agent_response: str
    expected_outcome: OutcomeClassification
    actual_outcome: OutcomeClassification
    passed: bool
    is_false_resolution: bool
    verification_reason: str
    latency_ms: float
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

class EvalSummary(BaseModel):
    suite_name: str
    total_scenarios: int
    completion_rate: float
    correct_escalation_rate: float
    false_resolution_rate: float
    failure_rate: float
    overall_pass_rate: float
    average_latency_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    results: List[ScenarioResult] = Field(default_factory=list)

class ComparisonReport(BaseModel):
    baseline_summary: EvalSummary
    improved_summary: EvalSummary
    false_resolution_reduction_pct: float
    completion_rate_delta: float
    notes: str
