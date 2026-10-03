"use client";

import React, { useState } from "react";
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Database, 
  FileText
} from "lucide-react";
import { VerificationResult, EHRSnapshot, EHRAppointment, EHREvent } from "../lib/api";

interface OutcomeVerificationPaneProps {
  verification: VerificationResult | null;
  ehrSnapshot: EHRSnapshot | null;
}

export const OutcomeVerificationPane: React.FC<OutcomeVerificationPaneProps> = ({
  verification,
  ehrSnapshot,
}) => {
  const [activeTab, setActiveTab] = useState<"outcome" | "ehr">("outcome");

  if (!verification) {
    return (
      <div className="flex flex-col h-full rounded-[12px] border border-[var(--border)] bg-[var(--surface)] p-6 items-center justify-center text-center text-[var(--text-muted)] text-[12px]">
        <ShieldCheck className="w-5 h-5 text-[var(--text-muted)] stroke-[1.5] mb-2" />
        <p className="font-medium text-[var(--text)]">Awaiting workflow execution</p>
        <p className="text-[12px] text-[var(--text-muted)] mt-1">Ground-truth verification results will appear here</p>
      </div>
    );
  }

  const { classification, reason, expected_outcome, actual_outcome, evidence, discrepancy_detected } = verification;

  // Outcome Badge Configurations (monochrome, with red reserved for false resolution / errors)
  const getBadgeConfig = () => {
    switch (classification) {
      case "COMPLETED":
        return {
          label: "Completed",
          border: "border-[var(--border)]",
          bg: "bg-[var(--subtle)]",
          text: "text-[var(--text)]",
          icon: <CheckCircle className="w-4 h-4 text-[var(--text)] stroke-[1.5]" />,
          subtitle: "Verified against clinical EHR ground truth",
        };
      case "CORRECTLY_ESCALATED":
        return {
          label: "Correctly escalated",
          border: "border-[var(--border)]",
          bg: "bg-[var(--subtle)]",
          text: "text-[var(--text)]",
          icon: <ShieldCheck className="w-4 h-4 text-[var(--text)] stroke-[1.5]" />,
          subtitle: "Safely handed off to human clinical staff",
        };
      case "FALSE_RESOLUTION":
        return {
          label: "False resolution detected",
          border: "border-[var(--danger)]",
          bg: "bg-[var(--danger-subtle)]",
          text: "text-[var(--danger)]",
          icon: <AlertTriangle className="w-4 h-4 text-[var(--danger)] stroke-[1.5]" />,
          subtitle: "Agent claimed success without matching EHR records",
        };
      case "FAILED":
      default:
        return {
          label: "Failed",
          border: "border-[var(--danger)]",
          bg: "bg-[var(--danger-subtle)]",
          text: "text-[var(--danger)]",
          icon: <XCircle className="w-4 h-4 text-[var(--danger)] stroke-[1.5]" />,
          subtitle: "Workflow incomplete or unescalated error",
        };
    }
  };

  const badge = getBadgeConfig();
  const appointmentsList = ehrSnapshot?.appointments
    ? (Array.isArray(ehrSnapshot.appointments)
        ? ehrSnapshot.appointments
        : Object.values(ehrSnapshot.appointments))
    : [];

  return (
    <div className="flex flex-col h-full rounded-[12px] border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      {/* Pane header with segmented tab switcher */}
      <div className="h-12 px-4 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between shrink-0">
        <div className="inline-flex h-8 p-0.5 rounded-[8px] bg-[var(--subtle)] border border-[var(--border)] max-w-full">
          <button
            type="button"
            onClick={() => setActiveTab("outcome")}
            className={`h-7 px-2 sm:px-3 rounded-[8px] text-[11px] sm:text-[12px] font-medium transition-colors duration-100 whitespace-nowrap ${
              activeTab === "outcome"
                ? "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)]"
                : "text-[var(--text-muted)] hover:text-[var(--text)] border-transparent"
            }`}
          >
            Verification
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("ehr")}
            className={`h-7 px-2 sm:px-3 rounded-[8px] text-[11px] sm:text-[12px] font-medium transition-colors duration-100 flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === "ehr"
                ? "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)]"
                : "text-[var(--text-muted)] hover:text-[var(--text)] border-transparent"
            }`}
          >
            <Database className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>Clinical EHR</span>
          </button>
        </div>

        <span className="text-[12px] text-[var(--text-muted)]">
          Independent verifier
        </span>
      </div>

      {/* Pane content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === "outcome" ? (
          <>
            {/* Primary outcome card */}
            <div className={`rounded-[8px] p-3 border ${badge.border} ${badge.bg}`}>
              <div className="flex items-start gap-2.5">
                <div className="mt-0.5 shrink-0">
                  {badge.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[13px] font-semibold ${badge.text}`}>
                      {badge.label}
                    </span>
                  </div>
                  <p className="text-[12px] text-[var(--text-muted)] mt-0.5">{badge.subtitle}</p>
                </div>
              </div>
            </div>

            {/* Verifier reasoning */}
            <div className="rounded-[8px] p-3 border border-[var(--border)] bg-[var(--subtle)] space-y-1">
              <div className="text-[12px] font-medium text-[var(--text-muted)] flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 stroke-[1.5]" />
                <span>Verification rationale</span>
              </div>
              <p className="text-[13px] text-[var(--text)] leading-relaxed">{reason}</p>
            </div>

            {/* Expected vs Actual */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12px]">
              <div className="rounded-[8px] p-3 border border-[var(--border)] bg-[var(--surface)]">
                <span className="text-[var(--text-muted)] block text-[12px]">Expected outcome</span>
                <span className="text-[var(--text)] font-medium mt-1 block">{expected_outcome}</span>
              </div>
              <div className="rounded-[8px] p-3 border border-[var(--border)] bg-[var(--surface)]">
                <span className="text-[var(--text-muted)] block text-[12px]">Actual clinical EHR outcome</span>
                <span className={`font-medium mt-1 block ${discrepancy_detected ? "text-[var(--danger)]" : "text-[var(--text)]"}`}>
                  {actual_outcome}
                </span>
              </div>
            </div>

            {/* Evidence items */}
            {evidence && evidence.length > 0 && (
              <div className="space-y-2 pt-1">
                <div className="text-[12px] font-medium text-[var(--text-muted)] flex items-center justify-between">
                  <span>Ground-truth evidence ({evidence.length})</span>
                  {discrepancy_detected && (
                    <span className="text-[12px] text-[var(--danger)] bg-[var(--danger-subtle)] px-2 py-0.5 rounded-[8px] border border-[var(--danger)]">
                      Discrepancy detected
                    </span>
                  )}
                </div>

                <div className="space-y-2">
                  {evidence.map((item, idx) => (
                    <div
                      key={idx}
                      className={`rounded-[8px] p-3 text-[12px] border ${
                        item.discrepancy
                          ? "bg-[var(--danger-subtle)] border-[var(--danger)]"
                          : "bg-[var(--subtle)] border border-[var(--border)]"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[12px] mb-1">
                        <span className="font-medium text-[var(--text)]">{item.field}</span>
                        <span className="text-[var(--text-muted)]">Source: {item.source}</span>
                      </div>
                      <div className="space-y-0.5">
                        {item.claimed_value && (
                          <div>
                            <span className="text-[var(--text-muted)]">Agent claim: </span>
                            <span className="text-[var(--text)] font-mono">{item.claimed_value}</span>
                          </div>
                        )}
                        {item.actual_value && (
                          <div>
                            <span className="text-[var(--text-muted)]">Clinical EHR state: </span>
                            <span className={`font-mono font-medium ${item.discrepancy ? "text-[var(--danger)]" : "text-[var(--text)]"}`}>
                              {item.actual_value}
                            </span>
                          </div>
                        )}
                      </div>
                      <p className="mt-1 text-[var(--text-muted)] italic">{item.details}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          /* Clinical EHR live records */
          <div className="space-y-4">
            <div>
              <div className="text-[12px] font-medium text-[var(--text-muted)] mb-2 flex items-center justify-between">
                <span>Active appointments in clinical EHR ({appointmentsList.length})</span>
                <span className="text-[12px] text-[var(--text-muted)]">Ground truth sync</span>
              </div>
              <div className="space-y-2">
                {appointmentsList.map((appt: EHRAppointment) => (
                  <div
                    key={appt.id}
                    className="rounded-[8px] p-3 bg-[var(--subtle)] border border-[var(--border)] text-[12px] space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--text)] font-semibold">{appt.id}</span>
                      <span
                        className={`text-[12px] px-2 py-0.5 rounded-[8px] font-medium ${
                          appt.status === "scheduled" || appt.status === "rescheduled"
                            ? "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)]"
                            : "bg-[var(--danger-subtle)] text-[var(--danger)] border border-[var(--danger)]"
                        }`}
                      >
                        {appt.status}
                      </span>
                    </div>
                    <div className="text-[var(--text)] font-medium">
                      {appt.procedure_type?.toUpperCase()} · {appt.location}
                    </div>
                    <div className="text-[var(--text-muted)]">
                      Scheduled time: <strong className="text-[var(--text)] font-medium">{new Date(appt.scheduled_time).toLocaleString()}</strong>
                    </div>
                    {appt.notes && (
                      <div className="text-[var(--text-muted)] italic truncate">
                        Notes: {appt.notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Workflow events inspector */}
            {ehrSnapshot?.workflow_events && (
              <div>
                <div className="text-[12px] font-medium text-[var(--text-muted)] mb-2">
                  Recent EHR workflow events ({ehrSnapshot.workflow_events.length})
                </div>
                <div className="divide-y divide-[var(--border)] rounded-[8px] border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
                  {ehrSnapshot.workflow_events.map((evt: EHREvent, i: number) => (
                    <div
                      key={i}
                      className="h-11 px-3 flex items-center justify-between text-[12px]"
                    >
                      <span className="text-[var(--text)] font-medium">{evt.event_type}</span>
                      <span className="text-[var(--text-muted)]">{evt.result}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};


