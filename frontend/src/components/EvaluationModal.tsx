"use client";

import React, { useState, useEffect } from "react";
import { X, Play, BarChart2, RefreshCw } from "lucide-react";
import { runNewComparison, EvalComparisonResponse, EvalScenarioResult, EvalSuiteSummary } from "../lib/api";

interface EvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportData: EvalComparisonResponse | null;
  onRefreshReport: (data: EvalComparisonResponse) => void;
}

export const EvaluationModal: React.FC<EvaluationModalProps> = ({
  isOpen,
  onClose,
  reportData,
  onRefreshReport,
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const baseline = reportData?.baseline || (reportData as unknown as { baseline_summary?: EvalSuiteSummary })?.baseline_summary;
  const improved = reportData?.improved || (reportData as unknown as { improved_summary?: EvalSuiteSummary })?.improved_summary;
  const results: EvalScenarioResult[] = improved?.results || [];

  const handleRunBenchmark = async () => {
    try {
      setIsRunning(true);
      const newReport = await runNewComparison();
      onRefreshReport(newReport);
    } catch (e) {
      alert("Failed to run benchmark suite: " + e);
    } finally {
      setIsRunning(false);
    }
  };

  const categories = ["ALL", ...Array.from(new Set(results.map((r: EvalScenarioResult) => r.category)))];
  const filteredResults = selectedCategory === "ALL"
    ? results
    : results.filter((r: EvalScenarioResult) => r.category === selectedCategory);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="eval-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs transition-opacity"
    >
      <div className="relative w-full max-w-[1000px] max-h-[90vh] bg-[var(--surface)] border border-[var(--border)] rounded-[12px] shadow-[0_1px_2px_rgba(0,0,0,0.05)] flex flex-col overflow-hidden text-[var(--text)]">
        {/* Modal header */}
        <div className="h-14 px-5 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <BarChart2 className="w-4 h-4 text-[var(--text-muted)] stroke-[1.5]" />
            <div>
              <h2 id="eval-modal-title" className="text-[14px] font-semibold text-[var(--text)]">
                36-scenario evaluation & false-resolution benchmark
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRunBenchmark}
              disabled={isRunning}
              className="btn-base btn-primary h-9 px-3.5 text-[13px] rounded-[8px] disabled:opacity-40"
            >
              {isRunning ? <RefreshCw className="w-3.5 h-3.5 animate-spin stroke-[1.5]" /> : <Play className="w-3.5 h-3.5 stroke-[1.5]" />}
              <span>{isRunning ? "Running tests..." : "Run benchmark suite"}</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="btn-base btn-ghost h-9 w-9 p-0 rounded-[8px] text-[var(--text-muted)] hover:text-[var(--text)]"
            >
              <X className="w-4 h-4 stroke-[1.5]" />
            </button>
          </div>
        </div>

        {/* Modal body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Key KPI Delta comparison cards */}
          <div>
            <h3 className="text-[12px] font-medium text-[var(--text-muted)] mb-2.5">
              Improvement loop metrics: baseline vs production agent
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-[12px]">
              {/* Primary metric: False resolution */}
              <div className="rounded-[8px] p-3 border border-[var(--danger)] bg-[var(--danger-subtle)]">
                <span className="text-[12px] font-semibold text-[var(--danger)] block">
                  False resolution rate
                </span>
                <div className="mt-2 flex items-baseline justify-between">
                  <div>
                    <span className="text-[12px] text-[var(--text-muted)] block">Baseline:</span>
                    <span className="text-[14px] font-semibold text-[var(--danger)]">{baseline?.false_resolution_rate ?? "5.56"}%</span>
                  </div>
                  <span className="text-[14px] text-[var(--text-muted)]">→</span>
                  <div className="text-right">
                    <span className="text-[12px] text-[var(--text-muted)] block font-medium">Production:</span>
                    <span className="text-[14px] font-semibold text-[var(--text)]">{improved?.false_resolution_rate ?? "0.0"}%</span>
                  </div>
                </div>
              </div>

              {/* Completion rate */}
              <div className="rounded-[8px] p-3 border border-[var(--border)] bg-[var(--subtle)]">
                <span className="text-[12px] font-medium text-[var(--text-muted)] block">
                  Completion rate
                </span>
                <div className="mt-2 flex items-baseline justify-between">
                  <div>
                    <span className="text-[12px] text-[var(--text-muted)] block">Baseline:</span>
                    <span className="text-[14px] text-[var(--text)]">{baseline?.completion_rate ?? "38.89"}%</span>
                  </div>
                  <span className="text-[14px] text-[var(--text-muted)]">→</span>
                  <div className="text-right">
                    <span className="text-[12px] text-[var(--text-muted)] block">Production:</span>
                    <span className="text-[14px] font-semibold text-[var(--text)]">{improved?.completion_rate ?? "33.33"}%</span>
                  </div>
                </div>
              </div>

              {/* Correct escalation rate */}
              <div className="rounded-[8px] p-3 border border-[var(--border)] bg-[var(--subtle)]">
                <span className="text-[12px] font-medium text-[var(--text-muted)] block">
                  Correct escalation
                </span>
                <div className="mt-2 flex items-baseline justify-between">
                  <div>
                    <span className="text-[12px] text-[var(--text-muted)] block">Baseline:</span>
                    <span className="text-[14px] text-[var(--text)]">{baseline?.correct_escalation_rate ?? "52.78"}%</span>
                  </div>
                  <span className="text-[14px] text-[var(--text-muted)]">→</span>
                  <div className="text-right">
                    <span className="text-[12px] text-[var(--text-muted)] block">Production:</span>
                    <span className="text-[14px] font-semibold text-[var(--text)]">{improved?.correct_escalation_rate ?? "66.67"}%</span>
                  </div>
                </div>
              </div>

              {/* Average latency */}
              <div className="rounded-[8px] p-3 border border-[var(--border)] bg-[var(--subtle)]">
                <span className="text-[12px] font-medium text-[var(--text-muted)] block">
                  Average latency
                </span>
                <div className="mt-2 flex items-baseline justify-between">
                  <div>
                    <span className="text-[12px] text-[var(--text-muted)] block">Baseline:</span>
                    <span className="text-[14px] text-[var(--text)]">{baseline?.avg_latency_ms ?? "0.66"} ms</span>
                  </div>
                  <span className="text-[14px] text-[var(--text-muted)]">→</span>
                  <div className="text-right">
                    <span className="text-[12px] text-[var(--text-muted)] block">Active:</span>
                    <span className="text-[14px] font-semibold text-[var(--text)]">{improved?.avg_latency_ms ?? "0.58"} ms</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Category filter pills */}
          <div>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
              {categories.map((cat, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setSelectedCategory(cat)}
                  className={`btn-base h-7 px-2.5 text-[12px] rounded-[8px] transition-colors duration-100 whitespace-nowrap ${
                    selectedCategory === cat
                      ? "bg-[var(--text)] text-[var(--surface)] border-[var(--text)] font-medium"
                      : "btn-secondary text-[var(--text-muted)] hover:text-[var(--text)]"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Results table: 1px row dividers, no zebra stripes, 44px rows */}
          <div className="rounded-[8px] border border-[var(--border)] overflow-hidden bg-[var(--surface)]">
            <table className="w-full text-left border-collapse text-[12px]">
              <thead>
                <tr className="bg-[var(--subtle)] text-[var(--text-muted)] border-b border-[var(--border)] h-9">
                  <th className="px-3 font-medium">Scenario id</th>
                  <th className="px-3 font-medium">Category</th>
                  <th className="px-3 font-medium">User prompt</th>
                  <th className="px-3 font-medium">Outcome</th>
                  <th className="px-3 font-medium">Verifier reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {filteredResults.map((r: EvalScenarioResult, idx: number) => {
                  const isFalseRes = r.actual_outcome === "FALSE_RESOLUTION";
                  return (
                    <tr key={idx} className="h-11 hover:bg-[var(--subtle)] transition-colors duration-100">
                      <td className="px-3 font-medium text-[var(--text)] whitespace-nowrap">{r.scenario_id}</td>
                      <td className="px-3 text-[var(--text-muted)] whitespace-nowrap">{r.category}</td>
                      <td className="px-3 text-[var(--text)] max-w-xs truncate" title={r.user_input}>
                        {r.user_input}
                      </td>
                      <td className="px-3 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 rounded-[8px] text-[12px] font-medium ${
                            isFalseRes
                              ? "bg-[var(--danger-subtle)] text-[var(--danger)] border border-[var(--danger)]"
                              : "bg-[var(--subtle)] text-[var(--text)] border border-[var(--border)]"
                          }`}
                        >
                          {r.actual_outcome}
                        </span>
                      </td>
                      <td className="px-3 text-[var(--text-muted)] max-w-sm truncate" title={r.verification_reason}>
                        {r.verification_reason}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};


