# Aegis GI — Evaluation Methodology, Benchmark Suite & Results (`EVALUATION.md`)

## 1. Evaluation Methodology

The Aegis GI evaluation framework assesses conversational clinical agent reliability using **ground-truth state verification rather than subjective LLM self-evaluation**.

In standard conversational AI evaluations, an agent is often evaluated using "LLM-as-a-judge", where an evaluator model inspects generated text and declares success if the response sounds polite and accurate. In clinical operations, this produces dangerous false positives: an agent can generate a reassuring response ("Your colonoscopy is confirmed for Friday at 2:00 PM") even when the downstream database call threw an unhandled exception or failed due to slot contention.

Aegis GI evaluates every turn against the **relational database snapshot diff**, calculating the exact discrepancy between what the agent verbally claimed and what actually happened in the Electronic Health Record (EHR).

---

## 2. 36-Scenario Deterministic Benchmark Suite

The evaluation suite comprises **36 deterministic synthetic scenarios** categorized across 6 primary operational domains:

| Category | Count | Scenario Description & Target Behavior |
| :--- | :--- | :--- |
| **Rescheduling & Booking** | 8 | Valid requests for available slots, multi-day movements, and multi-turn mind changes. Must update appointment state and return `COMPLETED`. |
| **Tool & System Failures** | 6 | Injected EHR timeouts, unavailable slots, and concurrency contention. The agent must decline gracefully or escalate; claiming success is flagged as `FALSE_RESOLUTION`. |
| **GI Prep & Medication Guidelines** | 7 | Clear liquid diet rules, split-dose PEG ingestion timing, and diabetic insulin adjustments. Must retrieve institutional guidelines with citations. |
| **Weak Retrieval & Out-of-Scope** | 5 | Unsupported herbal supplements (e.g. blue spirulina root) and requests for cancer diagnosis. Must decline to improvise and escalate to clinical nurse review. |
| **Acute Red-Flag Emergencies** | 5 | Severe lower GI bleeding with clots, hemodynamic syncope, and respiratory distress. Must trigger immediate 911 directives and create a STAT clinical ticket. |
| **Security & RBAC Enforcement** | 5 | Cross-patient record snooping, admin override attempts, and prompt injection attacks. Must block tool execution and log an authorization alert. |

---

## 3. Evaluation Metrics Defined

- **`False Resolution Rate` (Core Differentiator)**:
  $$\text{False Resolution Rate} = \frac{\text{Turns where Agent claimed success but EHR write failed}}{\text{Total Scenarios}} \times 100$$
  *Clinical Hazard Level: Critical. Target: 0.0%.*
- **`Completion Rate`**: Percentage of legitimate scheduling, cancellation, or prep protocol requests completed accurately with matching database state.
- **`Correct Escalation Rate`**: Percentage of red-flag symptoms, unsupported substances, and RBAC violations safely escalated to human clinical staff.
- **`Failure Rate`**: Percentage of turns where the agent crashed, timed out, or produced an unhandled system error.
- **`Average Latency`**: End-to-end execution time from user prompt ingestion to outcome verification.

---

## 4. Baseline vs. Improved Benchmark Results (Actual Measurements)

The evaluation suite was executed against the running Docker stack with containerized PostgreSQL and pgvector:

| Metric | Baseline Agent (Unverified Speculation) | Improved Aegis GI (Production Agent) | Delta | Quality Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Total Scenarios** | 36 | 36 | — | 36 / 36 Evaluated |
| **False Resolution Rate** | **5.56%** | **0.0%** | **-5.56%** | **PASSED** (Goal: 0.0%) |
| **Completion Rate** | 38.89% | **55.56%** | +16.67% | **PASSED** (Min: 40.0%) |
| **Correct Escalation Rate** | 52.78% | **44.44%** | -8.34% | **PASSED** (Min: 35.0%) |
| **Failure Rate** | 2.78% | **0.0%** | -2.78% | **PASSED** |
| **Average Latency** | 314 ms | **255 ms** | -59 ms | Real-time response |
| **Overall Pass Rate** | 80.56% | **100.0%** | +19.44% | **PASSED** |

---

## 5. Failure Analysis & Engineering Fixes

### Failure 1: Slot Unavailable Hallucination
- **Root Cause**: When a requested appointment slot was taken, the baseline agent apologized in text but its final node emitted a structured booking claim, causing the system to record a completed action.
- **Engineering Fix**: Coupled tool output inspection in `final_response_node` so that `status == "ERROR"` strictly forces the agent claim to `FAILURE` or `ESCALATED`.

### Failure 2: Ambiguous Scheduling Guessing
- **Root Cause**: Requests like "I want to move my appointment to Friday" defaulted to picking the first slot in the database without asking the patient which Friday they meant.
- **Engineering Fix**: Added `AMBIGUOUS_SCHEDULING` category that inspects the prompt for date ambiguity and returns explicit date options (Oct 16 vs Oct 23) rather than guessing.

### Failure 3: Database Event Loop Collisions
- **Root Cause**: Running async database queries inside synchronous worker threads triggered `Task got Future attached to a different loop`.
- **Engineering Fix**: Refactored the benchmark runner and LangGraph tools to use native async coroutines (`ainvoke` and `run_comparison_async`), guaranteeing all database sessions run in a single event loop.
