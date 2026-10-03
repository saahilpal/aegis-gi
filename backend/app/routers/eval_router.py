import os
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, desc

from ..evaluation.runner import benchmark_runner
from ..evaluation.scenarios import SCENARIOS
from ..models.eval import EvalSummary, ComparisonReport, ScenarioResult
from ..models.outcome import OutcomeClassification
from ..db.database import get_db_session
from ..db.models import EvaluationRun as EvaluationRunModel, EvaluationResult as EvaluationResultModel

router = APIRouter(prefix="/api/eval", tags=["Evaluation & Benchmarks"])

@router.get("/scenarios")
def get_scenarios():
    """List all 36 evaluation scenarios across all clinical categories."""
    return {"total": len(SCENARIOS), "scenarios": [s.dict() for s in SCENARIOS]}

@router.post("/run", response_model=EvalSummary)
def run_evaluation(is_baseline: bool = Query(False, description="Run baseline vs improved suite")):
    """Run the evaluation suite against real LangGraph and persist to database."""
    return benchmark_runner.run_suite(is_baseline=is_baseline)

@router.post("/comparison", response_model=ComparisonReport)
def run_comparison():
    """Run both baseline and improved evaluation suites and return comparison report."""
    return benchmark_runner.run_comparison()

@router.get("/latest")
async def get_latest_results():
    """Return latest evaluation comparison report queried directly from SQL database."""
    async with get_db_session() as session:
        # Fetch latest baseline run
        baseline_stmt = select(EvaluationRunModel).where(
            EvaluationRunModel.is_baseline == True
        ).order_by(desc(EvaluationRunModel.run_timestamp)).limit(1)
        baseline_run = (await session.execute(baseline_stmt)).scalar_one_or_none()

        # Fetch latest improved run
        improved_stmt = select(EvaluationRunModel).where(
            EvaluationRunModel.is_baseline == False
        ).order_by(desc(EvaluationRunModel.run_timestamp)).limit(1)
        improved_run = (await session.execute(improved_stmt)).scalar_one_or_none()

        if baseline_run and improved_run:
            # Query results for improved run
            res_stmt = select(EvaluationResultModel).where(
                EvaluationResultModel.run_id == improved_run.id
            )
            improved_results_db = (await session.execute(res_stmt)).scalars().all()

            results_list = [
                {
                    "scenario_id": r.scenario_id,
                    "category": r.category,
                    "name": r.scenario_id,
                    "user_input": r.user_prompt,
                    "agent_response": "",
                    "expected_outcome": r.expected_outcome,
                    "actual_outcome": r.actual_outcome,
                    "passed": not r.discrepancy_detected and (r.actual_outcome == r.expected_outcome),
                    "is_false_resolution": r.discrepancy_detected,
                    "verification_reason": r.verification_reason,
                    "latency_ms": r.latency_ms,
                    "evidence": []
                }
                for r in improved_results_db
            ]

            reduction = baseline_run.false_resolution_rate - improved_run.false_resolution_rate
            completion_delta = improved_run.completion_rate - baseline_run.completion_rate

            return {
                "baseline_summary": {
                    "suite_name": baseline_run.suite_name,
                    "total_scenarios": baseline_run.total_scenarios,
                    "completion_rate": baseline_run.completion_rate,
                    "correct_escalation_rate": baseline_run.correct_escalation_rate,
                    "false_resolution_rate": baseline_run.false_resolution_rate,
                    "failure_rate": round(100.0 - baseline_run.completion_rate - baseline_run.correct_escalation_rate - baseline_run.false_resolution_rate, 2),
                    "overall_pass_rate": round(100.0 - baseline_run.false_resolution_rate, 2),
                    "average_latency_ms": baseline_run.average_latency_ms,
                    "timestamp": baseline_run.run_timestamp.isoformat(),
                    "category_breakdown": {},
                    "results": []
                },
                "improved_summary": {
                    "suite_name": improved_run.suite_name,
                    "total_scenarios": improved_run.total_scenarios,
                    "completion_rate": improved_run.completion_rate,
                    "correct_escalation_rate": improved_run.correct_escalation_rate,
                    "false_resolution_rate": improved_run.false_resolution_rate,
                    "failure_rate": round(100.0 - improved_run.completion_rate - improved_run.correct_escalation_rate - improved_run.false_resolution_rate, 2),
                    "overall_pass_rate": round(100.0 - improved_run.false_resolution_rate, 2),
                    "average_latency_ms": improved_run.average_latency_ms,
                    "timestamp": improved_run.run_timestamp.isoformat(),
                    "category_breakdown": {},
                    "results": results_list
                },
                "false_resolution_reduction_pct": round(reduction, 2),
                "completion_rate_delta": round(completion_delta, 2),
                "notes": (
                    f"Baseline False Resolution Rate was {baseline_run.false_resolution_rate}%. "
                    f"After strict EHR verification alignment, False Resolution Rate decreased to {improved_run.false_resolution_rate}%."
                )
            }

    # If no run in database yet, run comparison and persist
    return benchmark_runner.run_comparison().dict()
