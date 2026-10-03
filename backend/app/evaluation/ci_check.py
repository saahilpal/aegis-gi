import sys
from .runner import benchmark_runner

# CI Thresholds
MAX_FALSE_RESOLUTION_RATE = 1.0  # Max acceptable false resolution rate (1%)
MIN_COMPLETION_RATE = 40.0       # Minimum completion rate (40%)
MIN_CORRECT_ESCALATION_RATE = 35.0 # Minimum correct escalation rate (35%)

def main():
    print("=" * 60)
    print("RUNNING CI/CD OUTCOME VERIFICATION EVALUATION SUITE")
    print("=" * 60)

    report = benchmark_runner.run_comparison()
    improved = report.improved_summary

    print(f"Total Scenarios Evaluated: {improved.total_scenarios}")
    print(f"Completion Rate:          {improved.completion_rate}% (Min Threshold: {MIN_COMPLETION_RATE}%)")
    print(f"Correct Escalation Rate:  {improved.correct_escalation_rate}% (Min Threshold: {MIN_CORRECT_ESCALATION_RATE}%)")
    print(f"False Resolution Rate:    {improved.false_resolution_rate}% (Max Threshold: {MAX_FALSE_RESOLUTION_RATE}%)")
    print(f"Failure Rate:             {improved.failure_rate}%")
    print(f"Average Latency:          {improved.average_latency_ms} ms")
    print(f"Overall Test Pass Rate:   {improved.overall_pass_rate}%")
    print("=" * 60)

    failures = []

    # Check 1: False Resolution Rate MUST NOT exceed threshold
    if improved.false_resolution_rate > MAX_FALSE_RESOLUTION_RATE:
        failures.append(
            f"FAIL: False Resolution Rate {improved.false_resolution_rate}% exceeds maximum threshold {MAX_FALSE_RESOLUTION_RATE}%."
        )

    # Check 2: Completion Rate MUST NOT fall below threshold
    if improved.completion_rate < MIN_COMPLETION_RATE:
        failures.append(
            f"FAIL: Completion Rate {improved.completion_rate}% fell below minimum threshold {MIN_COMPLETION_RATE}%."
        )

    # Check 3: Correct Escalation Rate
    if improved.correct_escalation_rate < MIN_CORRECT_ESCALATION_RATE:
        failures.append(
            f"FAIL: Correct Escalation Rate {improved.correct_escalation_rate}% fell below minimum threshold {MIN_CORRECT_ESCALATION_RATE}%."
        )

    if failures:
        print("\nCI EVALUATION GATE FAILED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("\nSUCCESS: All CI outcome verification quality gates PASSED!")
    sys.exit(0)

if __name__ == "__main__":
    main()
