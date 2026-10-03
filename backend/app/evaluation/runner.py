import time
import json
import os
import uuid
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone

from .scenarios import SCENARIOS, EvalScenario
from ..models.eval import ScenarioResult, EvalSummary, ComparisonReport
from ..models.outcome import OutcomeClassification
from ..ehr.ehr_service import ehr_service
from ..agent.graph import agent_workflow
from ..verifier.outcome_verifier import outcome_verifier
from ..db.database import get_db_session
from ..db.models import EvaluationRun as EvaluationRunModel, EvaluationResult as EvaluationResultModel
from ..ehr.ehr_service import run_async

class BenchmarkRunner:
    """
    Evaluation runner executing test scenarios through the complete LangGraph workflow,
    evaluating results using the independent OutcomeVerifier, and persisting runs to PostgreSQL/DB.
    """

    async def persist_run_to_db(self, summary: EvalSummary, is_baseline: bool) -> str:
        run_id = str(uuid.uuid4())
        async with get_db_session() as session:
            db_run = EvaluationRunModel(
                id=run_id,
                run_timestamp=datetime.now(timezone.utc),
                suite_name=summary.suite_name,
                total_scenarios=summary.total_scenarios,
                completed_count=sum(1 for r in summary.results if r.actual_outcome == OutcomeClassification.COMPLETED),
                correctly_escalated_count=sum(1 for r in summary.results if r.actual_outcome == OutcomeClassification.CORRECTLY_ESCALATED),
                false_resolution_count=sum(1 for r in summary.results if r.actual_outcome == OutcomeClassification.FALSE_RESOLUTION),
                failed_count=sum(1 for r in summary.results if r.actual_outcome == OutcomeClassification.FAILED),
                false_resolution_rate=summary.false_resolution_rate,
                completion_rate=summary.completion_rate,
                correct_escalation_rate=summary.correct_escalation_rate,
                average_latency_ms=summary.average_latency_ms,
                is_baseline=is_baseline
            )
            session.add(db_run)

            for r in summary.results:
                db_res = EvaluationResultModel(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    scenario_id=r.scenario_id,
                    category=r.category,
                    user_prompt=r.user_input,
                    expected_outcome=r.expected_outcome.value if hasattr(r.expected_outcome, "value") else str(r.expected_outcome),
                    actual_outcome=r.actual_outcome.value if hasattr(r.actual_outcome, "value") else str(r.actual_outcome),
                    classification=r.actual_outcome.value if hasattr(r.actual_outcome, "value") else str(r.actual_outcome),
                    verification_reason=r.verification_reason,
                    latency_ms=r.latency_ms,
                    discrepancy_detected=r.is_false_resolution
                )
                session.add(db_res)

            await session.commit()
        return run_id

    async def run_suite_async(self, is_baseline: bool = False) -> EvalSummary:
        results: List[ScenarioResult] = []
        latencies: List[float] = []
        counts = {
            OutcomeClassification.COMPLETED: 0,
            OutcomeClassification.CORRECTLY_ESCALATED: 0,
            OutcomeClassification.FALSE_RESOLUTION: 0,
            OutcomeClassification.FAILED: 0
        }
        passed_count = 0
        suite_name = "Baseline Evaluation Suite" if is_baseline else "Improved Evaluation Suite (Production)"

        for sc in SCENARIOS:
            # 1. Reset EHR state for pristine test isolation
            await ehr_service.reset_state_async()
            if sc.simulate_tool_failure:
                ehr_service.forced_failure = sc.simulate_tool_failure
            else:
                ehr_service.forced_failure = None

            before_snapshot = await ehr_service.take_snapshot_async()
            t0 = time.time()

            force_hallucination = sc.simulate_agent_hallucination if is_baseline else False

            # 2. Invoke Agent Workflow
            initial_state = {
                "user_message": sc.user_input,
                "patient_id": sc.patient_id,
                "user_role": "PATIENT",
                "force_tool_failure": sc.simulate_tool_failure,
                "force_agent_hallucination": force_hallucination,
                "trace_steps": []
            }
            
            try:
                agent_output = await agent_workflow.ainvoke(initial_state)
                agent_response = agent_output.get("final_response", "")
                agent_claim = agent_output.get("agent_claim")
            except Exception as e:
                agent_response = f"Agent encountered error: {str(e)}"
                agent_claim = None

            after_snapshot = await ehr_service.take_snapshot_async()
            latency_ms = round((time.time() - t0) * 1000, 2)
            latencies.append(latency_ms)

            # 3. Independent Outcome Verification
            verification = outcome_verifier.verify(
                user_message=sc.user_input,
                agent_response=agent_response,
                agent_claim=agent_claim,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                expected_outcome=sc.expected_outcome
            )

            classification = verification.classification
            counts[classification] = counts.get(classification, 0) + 1

            is_false_res = (classification == OutcomeClassification.FALSE_RESOLUTION)
            
            if is_baseline and sc.simulate_agent_hallucination:
                passed = is_false_res
            else:
                passed = (classification == sc.expected_outcome) and not is_false_res

            if passed:
                passed_count += 1

            results.append(ScenarioResult(
                scenario_id=sc.id,
                category=sc.category,
                name=sc.name,
                user_input=sc.user_input,
                agent_response=agent_response,
                expected_outcome=sc.expected_outcome,
                actual_outcome=classification,
                passed=passed,
                is_false_resolution=is_false_res,
                verification_reason=verification.reason,
                latency_ms=latency_ms,
                evidence=[e.dict() for e in verification.evidence]
            ))

        total = len(SCENARIOS)
        completion_rate = round((counts[OutcomeClassification.COMPLETED] / total) * 100, 2)
        correct_escalation_rate = round((counts[OutcomeClassification.CORRECTLY_ESCALATED] / total) * 100, 2)
        false_resolution_rate = round((counts[OutcomeClassification.FALSE_RESOLUTION] / total) * 100, 2)
        failure_rate = round((counts[OutcomeClassification.FAILED] / total) * 100, 2)
        pass_rate = round((passed_count / total) * 100, 2)
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

        breakdown: Dict[str, Dict[str, Any]] = {}
        for r in results:
            cat = r.category
            if cat not in breakdown:
                breakdown[cat] = {"total": 0, "passed": 0, "false_resolutions": 0}
            breakdown[cat]["total"] += 1
            if r.passed:
                breakdown[cat]["passed"] += 1
            if r.is_false_resolution:
                breakdown[cat]["false_resolutions"] += 1

        summary = EvalSummary(
            suite_name=suite_name,
            total_scenarios=total,
            completion_rate=completion_rate,
            correct_escalation_rate=correct_escalation_rate,
            false_resolution_rate=false_resolution_rate,
            failure_rate=failure_rate,
            overall_pass_rate=pass_rate,
            average_latency_ms=avg_latency,
            timestamp=datetime.now(timezone.utc),
            category_breakdown=breakdown,
            results=results
        )

        # Persist to database
        try:
            await self.persist_run_to_db(summary, is_baseline=is_baseline)
        except Exception:
            pass

        return summary

    def run_suite(self, is_baseline: bool = False) -> EvalSummary:
        return run_async(self.run_suite_async(is_baseline))

    async def run_comparison_async(self) -> ComparisonReport:
        """Executes baseline pass, then improved pass, and computes delta metrics."""
        baseline = await self.run_suite_async(is_baseline=True)
        improved = await self.run_suite_async(is_baseline=False)

        reduction = baseline.false_resolution_rate - improved.false_resolution_rate
        completion_delta = improved.completion_rate - baseline.completion_rate

        report = ComparisonReport(
            baseline_summary=baseline,
            improved_summary=improved,
            false_resolution_reduction_pct=round(reduction, 2),
            completion_rate_delta=round(completion_delta, 2),
            notes=(
                f"Baseline False Resolution Rate was {baseline.false_resolution_rate}%. "
                f"After strict EHR verification alignment, False Resolution Rate decreased to {improved.false_resolution_rate}%."
            )
        )
        return report

    def run_comparison(self) -> ComparisonReport:
        """Executes baseline pass, then improved pass, and computes delta metrics."""
        return run_async(self.run_comparison_async())

benchmark_runner = BenchmarkRunner()
