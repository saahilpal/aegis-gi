const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Citation {
  source_document: string;
  source_section: string;
  text_snippet: string;
  confidence: number;
}

export interface TraceStep {
  node_id: string;
  node_name: string;
  status: string;
  latency_ms: number;
  input_summary?: string;
  output_summary?: string;
  timestamp?: string;
}

export interface EvidenceItem {
  source: string;
  field: string;
  claimed_value?: string;
  actual_value?: string;
  discrepancy: boolean;
  details: string;
}

export interface VerificationResult {
  classification: "COMPLETED" | "CORRECTLY_ESCALATED" | "FALSE_RESOLUTION" | "FAILED";
  expected_outcome: string;
  actual_outcome: string;
  reason: string;
  evidence: EvidenceItem[];
  discrepancy_detected: boolean;
  ehr_verified_timestamp?: string;
}

export interface EHRAppointment {
  id: string;
  patient_id: string;
  provider_id: string;
  procedure_type: string;
  scheduled_time: string;
  status: string;
  location: string;
  notes?: string;
  reschedule_count?: number;
}

export interface EHREvent {
  id?: string;
  event_type: string;
  patient_id?: string;
  provider_id?: string;
  timestamp?: string;
  actor_role?: string;
  details?: Record<string, unknown>;
  status?: string;
  result?: string;
}

export interface EHRSnapshot {
  appointments?: Record<string, EHRAppointment> | EHRAppointment[];
  audit_events?: EHREvent[];
  workflow_events?: EHREvent[];
  active_appointments_count?: number;
  total_audit_events_count?: number;
  timestamp?: string;
}

export interface ClaimedAction {
  action_type: string;
  target_id?: string;
  details?: Record<string, unknown>;
}

export interface ChatResponse {
  conversation_id: string;
  response_text: string;
  citations: Citation[];
  claimed_action?: ClaimedAction;
  outcome_verification: VerificationResult;
  trace_steps: TraceStep[];
  ehr_snapshot?: EHRSnapshot;
  total_latency_ms: number;
}

export interface StreamCallbacks {
  onStatus?: (data: { message: string; status: string }) => void;
  onTraceStep?: (step: TraceStep) => void;
  onToken?: (token: string) => void;
  onOutcome?: (outcome: VerificationResult) => void;
  onEhrDiff?: (diff: Record<string, unknown>) => void;
  onDone?: (payload: { response_text: string; citations: Citation[]; total_latency_ms: number }) => void;
  onError?: (err: Error) => void;
}

export async function streamChatMessage(
  message: string,
  patientId: string = "P101",
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const url = new URL(`${API_BASE}/api/chat/stream`);
  url.searchParams.set("message", message);
  url.searchParams.set("patient_id", patientId);

  const res = await fetch(url.toString(), {
    headers: { Accept: "text/event-stream" },
    signal,
  });

  if (!res.ok) {
    throw new Error(`SSE Connection failed with status ${res.status}: ${res.statusText}`);
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("ReadableStream not supported on response body.");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "message";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = "message";
          continue;
        }

        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.replace("event:", "").trim();
          continue;
        }

        if (trimmed.startsWith("data:")) {
          const dataStr = trimmed.replace("data:", "").trim();
          if (!dataStr) continue;

          try {
            const parsed = JSON.parse(dataStr);

            switch (currentEvent) {
              case "status":
                callbacks.onStatus?.(parsed);
                break;
              case "trace_step":
                callbacks.onTraceStep?.(parsed);
                break;
              case "token":
                if (parsed.token) {
                  callbacks.onToken?.(parsed.token);
                }
                break;
              case "outcome":
                callbacks.onOutcome?.(parsed);
                break;
              case "ehr_diff":
                callbacks.onEhrDiff?.(parsed);
                break;
              case "done":
                callbacks.onDone?.(parsed);
                break;
              case "error":
                callbacks.onError?.(new Error(parsed.message || "Stream error"));
                break;
              default:
                break;
            }
          } catch (parseErr) {
            console.warn("Failed to parse SSE payload:", dataStr, parseErr);
          }
        }
      }
    }
  } catch (err: unknown) {
    const errorObj = err instanceof Error ? err : new Error(String(err));
    if (errorObj.name === "AbortError") {
      return;
    }
    callbacks.onError?.(errorObj);
    throw errorObj;
  } finally {
    reader.releaseLock();
  }
}

export async function sendChatMessage(
  message: string,
  patientId: string = "P101",
  forceToolFailure?: string,
  forceHallucination: boolean = false
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      patient_id: patientId,
      user_role: "PATIENT",
      force_tool_failure: forceToolFailure || null,
      force_agent_hallucination: forceHallucination,
    }),
  });
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchEhrSnapshot(): Promise<EHRSnapshot> {
  const res = await fetch(`${API_BASE}/api/ehr/snapshot`);
  if (!res.ok) throw new Error("Failed to fetch EHR snapshot");
  return res.json();
}

export async function resetEhr(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/ehr/reset`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to reset EHR");
  return res.json();
}
export const resetMockEhr = resetEhr;

export interface EvalScenarioResult {
  scenario_id: string;
  category: string;
  name: string;
  user_input: string;
  agent_response: string;
  expected_outcome: string;
  actual_outcome: string;
  passed: boolean;
  is_false_resolution: boolean;
  verification_reason: string;
  latency_ms: number;
  evidence: EvidenceItem[];
}

export interface EvalSuiteSummary {
  suite_name: string;
  total_scenarios: number;
  completed_count: number;
  escalated_count: number;
  false_resolution_count: number;
  failed_count: number;
  completion_rate: number;
  correct_escalation_rate: number;
  false_resolution_rate: number;
  failure_rate: number;
  avg_latency_ms: number;
  overall_passed: boolean;
  results: EvalScenarioResult[];
}

export interface EvalComparisonResponse {
  comparison_id: string;
  run_timestamp: string;
  baseline: EvalSuiteSummary;
  improved: EvalSuiteSummary;
  false_resolution_reduction: string;
  ci_quality_gate_passed: boolean;
}

export async function fetchEvalComparison(): Promise<EvalComparisonResponse> {
  const res = await fetch(`${API_BASE}/api/eval/latest`);
  if (!res.ok) throw new Error("Failed to fetch evaluation results");
  return res.json();
}

export async function runNewComparison(): Promise<EvalComparisonResponse> {
  const res = await fetch(`${API_BASE}/api/eval/comparison`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to run benchmark");
  return res.json();
}
