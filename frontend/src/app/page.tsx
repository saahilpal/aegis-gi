"use client";

import React, { useState, useEffect, useRef } from "react";
import { Header } from "../components/Header";
import { ChatPane, MessageItem } from "../components/ChatPane";
import { TracePane } from "../components/TracePane";
import { OutcomeVerificationPane } from "../components/OutcomeVerificationPane";
import { EvaluationModal } from "../components/EvaluationModal";
import { 
  streamChatMessage,
  sendChatMessage, 
  fetchEhrSnapshot, 
  resetEhr, 
  fetchEvalComparison,
  VerificationResult,
  TraceStep,
  EHRSnapshot,
  EvalComparisonResponse
} from "../lib/api";

export default function Home() {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "msg-init",
      role: "assistant",
      content: "Hello Sarah. I am your GI Prep & Booking Assistant for your upcoming screening colonoscopy at Gastroenterology Associates. How can I help you today with your appointment or preparation?",
      timestamp: "10:00 AM",
    },
  ]);

  const [traceSteps, setTraceSteps] = useState<TraceStep[]>([
    {
      node_id: "NODE-INIT",
      node_name: "Session Established",
      status: "COMPLETED",
      latency_ms: 1.2,
      output_summary: "Patient session Sarah Lin (#GI-89021) loaded from Clinical EHR",
    },
  ]);

  const [verification, setVerification] = useState<VerificationResult | null>({
    classification: "COMPLETED",
    expected_outcome: "Patient session initialized with Clinical EHR active appointment",
    actual_outcome: "Active appointment APT-1001 verified for 2026-10-15 10:00 AM",
    reason: "Session initialized nominal. Ground truth Clinical EHR state synced.",
    evidence: [
      {
        source: "CLINICAL_EHR",
        field: "appointments.APT-1001",
        claimed_value: "Active Colonoscopy",
        actual_value: "Scheduled (2026-10-15 10:00 AM)",
        discrepancy: false,
        details: "EHR ground truth matches baseline patient profile.",
      },
    ],
    discrepancy_detected: false,
  });

  const [ehrSnapshot, setEhrSnapshot] = useState<EHRSnapshot | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isEvalModalOpen, setIsEvalModalOpen] = useState(false);
  const [evalReport, setEvalReport] = useState<EvalComparisonResponse | null>(null);
  const [totalLatency, setTotalLatency] = useState(1.2);
  const [rightActiveView, setRightActiveView] = useState<"trace" | "verification">("verification");

  const abortControllerRef = useRef<AbortController | null>(null);

  // Load initial EHR snapshot and benchmark results
  useEffect(() => {
    fetchEhrSnapshot()
      .then((data) => setEhrSnapshot(data))
      .catch((err) => console.error("Could not fetch EHR snapshot:", err));

    fetchEvalComparison()
      .then((data) => setEvalReport(data))
      .catch((err) => console.error("Could not fetch eval comparison:", err));

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("benchmark") === "open") {
      requestAnimationFrame(() => {
        setIsEvalModalOpen(true);
      });
    }
  }, []);

  const handleSendMessage = async (text: string) => {
    // Abort previous in-flight stream if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsProcessing(true);
    const userMsg: MessageItem = {
      id: `msg-user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const assistantMsgId = `msg-assistant-${Date.now() + 1}`;
    const assistantMsg: MessageItem = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setTraceSteps([]);

    let accumulatedContent = "";

    try {
      await streamChatMessage(
        text,
        "P101",
        {
          onTraceStep: (step) => {
            setTraceSteps((prev) => {
              const existingIdx = prev.findIndex((s) => s.node_id === step.node_id);
              if (existingIdx >= 0) {
                const next = [...prev];
                next[existingIdx] = step;
                return next;
              }
              return [...prev, step];
            });
          },
          onToken: (token) => {
            accumulatedContent += token;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: accumulatedContent }
                  : m
              )
            );
          },
          onOutcome: (outcome) => {
            setVerification(outcome);
            const isRedFlag = outcome.classification === "CORRECTLY_ESCALATED" &&
              (text.toLowerCase().includes("bleeding") ||
               text.toLowerCase().includes("pain") ||
               text.toLowerCase().includes("breathe") ||
               text.toLowerCase().includes("emergency"));
            if (isRedFlag) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, isEmergency: true }
                    : m
                )
              );
            }
          },
          onDone: (payload) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: payload.response_text || accumulatedContent,
                      citations: payload.citations,
                      isStreaming: false,
                    }
                  : m
              )
            );
            if (payload.total_latency_ms) {
              setTotalLatency(payload.total_latency_ms);
            }
            fetchEhrSnapshot()
              .then((snap) => setEhrSnapshot(snap))
              .catch((err) => console.error("EHR refresh error:", err));
          },
          onError: (err) => {
            console.warn("Stream error, falling back to synchronous fetch:", err);
            // Fallback to standard POST
            sendChatMessage(text, "P101")
              .then((response) => {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? {
                          ...m,
                          content: response.response_text,
                          citations: response.citations,
                          isStreaming: false,
                        }
                      : m
                  )
                );
                setTraceSteps(response.trace_steps || []);
                setVerification(response.outcome_verification);
                setTotalLatency(response.total_latency_ms);
                fetchEhrSnapshot().then((snap) => setEhrSnapshot(snap));
              })
              .catch((fallbackErr) => {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? {
                          ...m,
                          content: `Error communicating with clinical assistant: ${fallbackErr.message}`,
                          isStreaming: false,
                        }
                      : m
                  )
                );
              });
          },
        },
        controller.signal
      );
    } catch (err: unknown) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      if (errorObj.name !== "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: m.content || `Communication interrupted: ${errorObj.message}`,
                  isStreaming: false,
                }
              : m
          )
        );
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRunDemo = async (demoNumber: 1 | 2 | 3) => {
    setIsProcessing(true);
    try {
      let promptText = "";
      let forceFailure: string | undefined = undefined;

      if (demoNumber === 1) {
        promptText = "I need to reschedule my colonoscopy on October 15th to late morning or afternoon.";
      } else if (demoNumber === 2) {
        promptText = "Can you reschedule my appointment? (EHR Gateway Failure Simulation)";
        forceFailure = "API_TIMEOUT";
      } else {
        promptText = "I drank the colonoscopy prep and now I have severe chest pain and dizziness.";
      }

      const userMsg: MessageItem = {
        id: `msg-${Date.now()}`,
        role: "user",
        content: promptText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, userMsg]);

      // Call real live backend workflow with outcome verification
      const response = await sendChatMessage(promptText, "P101", forceFailure);

      const assistantMsg: MessageItem = {
        id: `msg-${Date.now() + 1}`,
        role: "assistant",
        content: response.response_text,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        citations: response.citations,
        isEmergency: response.outcome_verification?.classification === "CORRECTLY_ESCALATED" && demoNumber === 3,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setTraceSteps(response.trace_steps || []);
      setVerification(response.outcome_verification);
      setTotalLatency(response.total_latency_ms);
      setRightActiveView("verification");

      // Refresh real database snapshot
      const newSnap = await fetchEhrSnapshot();
      setEhrSnapshot(newSnap);
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : String(err);
      alert(`Failed to execute clinical workflow: ${errMessage}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleResetEhr = async () => {
    try {
      await resetEhr();
      const freshSnap = await fetchEhrSnapshot();
      setEhrSnapshot(freshSnap);
      setMessages([
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: "Clinical EHR database has been reset to baseline clean state. All appointment schedules restored.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      setVerification({
        classification: "COMPLETED",
        expected_outcome: "Clinical EHR reset to baseline",
        actual_outcome: "Clean baseline state restored",
        reason: "Reset completed successfully.",
        evidence: [],
        discrepancy_detected: false,
      });
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : String(err);
      alert("Failed to reset EHR: " + errMessage);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[var(--bg)] text-[var(--text)] transition-colors">
      {/* Top Header */}
      <Header
        onRunDemo={handleRunDemo}
        onOpenEvalModal={() => setIsEvalModalOpen(true)}
        onResetEhr={handleResetEhr}
        isProcessing={isProcessing}
        activePatient="Sarah Lin (MRN #GI-89021)"
      />

      {/* Main Split-Screen Cockpit */}
      <main className="flex-1 p-4 md:p-6 max-w-[1100px] w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 min-h-[calc(100vh-56px)]">
        {/* Left Column: Patient Communication Channel (6 cols) */}
        <section className="lg:col-span-6 flex flex-col min-h-[580px] lg:min-h-0 lg:h-full">
          <ChatPane
            messages={messages}
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
          />
        </section>

        {/* Right Column: Observability & Outcome Verification Console (6 cols) */}
        <section className="lg:col-span-6 flex flex-col min-h-[580px] lg:min-h-0 lg:h-full">
          {/* Top Toggle Switcher for Right Pane */}
          <div className="flex items-center justify-between mb-3 px-0.5 flex-wrap gap-2 shrink-0">
            <div className="inline-flex h-9 p-0.5 rounded-[8px] bg-[var(--subtle)] border border-[var(--border)]">
              <button
                type="button"
                onClick={() => setRightActiveView("verification")}
                className={`h-8 px-2 sm:px-3 rounded-[8px] text-[12px] sm:text-[13px] font-medium transition-colors duration-100 whitespace-nowrap ${
                  rightActiveView === "verification"
                    ? "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text)] border-transparent"
                }`}
              >
                Verification & EHR
              </button>
              <button
                type="button"
                onClick={() => setRightActiveView("trace")}
                className={`h-8 px-2 sm:px-3 rounded-[8px] text-[12px] sm:text-[13px] font-medium transition-colors duration-100 whitespace-nowrap ${
                  rightActiveView === "trace"
                    ? "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text)] border-transparent"
                }`}
              >
                Trace ({traceSteps.length})
              </button>
            </div>
            <span className="text-[12px] text-[var(--text-muted)] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-[8px] bg-[var(--text-muted)]" />
              Independent verification active
            </span>
          </div>

          <div className="flex-1 min-h-0">
            {rightActiveView === "verification" ? (
              <OutcomeVerificationPane
                verification={verification}
                ehrSnapshot={ehrSnapshot}
              />
            ) : (
              <TracePane
                traceSteps={traceSteps}
                totalLatencyMs={totalLatency}
              />
            )}
          </div>
        </section>
      </main>

      {/* Evaluation & Benchmark Suite Modal */}
      <EvaluationModal
        isOpen={isEvalModalOpen}
        onClose={() => setIsEvalModalOpen(false)}
        reportData={evalReport}
        onRefreshReport={(data) => setEvalReport(data)}
      />
    </div>
  );
}

