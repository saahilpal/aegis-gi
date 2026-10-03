"use client";

import React, { useState } from "react";
import { CheckCircle2, ChevronRight, GitFork, ShieldAlert, Cpu, Database, Wrench, MessageSquare } from "lucide-react";
import { TraceStep } from "../lib/api";

interface TracePaneProps {
  traceSteps: TraceStep[];
  totalLatencyMs?: number;
}

export const TracePane: React.FC<TracePaneProps> = ({ traceSteps, totalLatencyMs = 0 }) => {
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  const getNodeIcon = (name: string) => {
    if (name.includes("Classification")) return <GitFork className="w-4 h-4 text-[var(--accent)] stroke-[1.5]" />;
    if (name.includes("Retrieval")) return <Database className="w-4 h-4 text-[var(--text-muted)] stroke-[1.5]" />;
    if (name.includes("Decide")) return <Cpu className="w-4 h-4 text-[var(--accent)] stroke-[1.5]" />;
    if (name.includes("Safety")) return <ShieldAlert className="w-4 h-4 text-[var(--text-muted)] stroke-[1.5]" />;
    if (name.includes("Tool")) return <Wrench className="w-4 h-4 text-[var(--text-muted)] stroke-[1.5]" />;
    return <MessageSquare className="w-4 h-4 text-[var(--text-muted)] stroke-[1.5]" />;
  };

  return (
    <div className="flex flex-col h-full rounded-[12px] border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      {/* Pane header */}
      <div className="h-12 px-4 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-[8px] bg-[var(--accent)]" />
          <h2 className="text-[13px] font-medium text-[var(--text)]">
            Execution trace
          </h2>
        </div>
        <span className="text-[12px] text-[var(--text-muted)]">
          Total latency: {totalLatencyMs.toFixed(1)} ms
        </span>
      </div>

      {/* Trace items list: 1px row dividers, 44px rows */}
      <div className="flex-1 overflow-y-auto divide-y divide-[var(--border)]">
        {traceSteps.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-center text-[var(--text-muted)] text-[12px] space-y-1">
            <Cpu className="w-4 h-4 text-[var(--text-muted)] stroke-[1.5]" />
            <p>Awaiting workflow invocation</p>
            <p className="text-[12px] text-[var(--text-muted)]">Execution nodes will appear as they complete</p>
          </div>
        ) : (
          traceSteps.map((step, idx) => {
            const isExpanded = expandedStep === step.node_id;

            return (
              <div key={step.node_id || idx} className="bg-[var(--surface)]">
                <button
                  type="button"
                  onClick={() => setExpandedStep(isExpanded ? null : step.node_id)}
                  className="w-full min-h-[44px] px-4 py-2.5 flex items-center justify-between gap-3 text-left hover:bg-[var(--subtle)] transition-colors duration-100"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-6 h-6 rounded-[8px] bg-[var(--subtle)] border border-[var(--border)] flex items-center justify-center shrink-0">
                      {getNodeIcon(step.node_name)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-medium text-[var(--text)] truncate">
                          {step.node_name}
                        </span>
                        {step.status === "INTERCEPTED" ? (
                          <span className="text-[12px] text-[var(--danger)] bg-[var(--danger-subtle)] border border-[var(--danger)] px-1.5 py-0.2 rounded-[8px]">
                            Safety flag
                          </span>
                        ) : step.status === "SKIPPED" ? (
                          <span className="text-[12px] text-[var(--text-muted)] bg-[var(--subtle)] border border-[var(--border)] px-1.5 py-0.2 rounded-[8px]">
                            Skipped
                          </span>
                        ) : (
                          <CheckCircle2 className="w-3.5 h-3.5 text-[var(--text-muted)] stroke-[1.5]" />
                        )}
                      </div>
                      <div className="text-[12px] text-[var(--text-muted)] truncate">
                        {step.output_summary}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[12px] text-[var(--text-muted)]">
                      {step.latency_ms.toFixed(1)} ms
                    </span>
                    <ChevronRight
                      className={`w-4 h-4 text-[var(--text-muted)] stroke-[1.5] transition-transform duration-100 ${
                        isExpanded ? "rotate-90" : ""
                      }`}
                    />
                  </div>
                </button>

                {/* Expanded detail drawer */}
                {isExpanded && (
                  <div className="px-4 py-3 bg-[var(--subtle)] border-t border-[var(--border)] text-[12px] space-y-1.5">
                    {step.input_summary && (
                      <div>
                        <span className="text-[var(--text-muted)]">Input: </span>
                        <span className="text-[var(--text)]">{step.input_summary}</span>
                      </div>
                    )}
                    {step.output_summary && (
                      <div>
                        <span className="text-[var(--text-muted)]">Output: </span>
                        <span className="text-[var(--text)]">{step.output_summary}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-[var(--text-muted)]">Node id: </span>
                      <span className="text-[var(--text-muted)]">{step.node_id}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};


