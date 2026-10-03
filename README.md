# Aegis GI: Outcome-Verified GI Prep & Booking Agent

[![CI/CD Quality Gate & Automated Deployment](https://github.com/nitrousoxide/aegis-gi/actions/workflows/ci.yml/badge.svg)](https://github.com/nitrousoxide/aegis-gi/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-zinc.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![PostgreSQL 18 + pgvector](https://img.shields.io/badge/PostgreSQL-18%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Cost: $0/month](https://img.shields.io/badge/Cost-%240%20%2F%20%E2%82%B90-success.svg)](COST.md)

> **A production-grade clinical AI agent engineered with an Independent Outcome Verification Engine to eliminate conversational false resolutions in gastroenterology procedure scheduling, bowel preparation guidance, and red-flag clinical triage.**

---

## 1. Value Proposition & Core Differentiator

In conventional conversational AI, conversational agents frequently claim operational tasks have succeeded when underlying downstream systems timed out, rejected writes, or threw unhandled errors.

In clinical gastroenterology—where procedural prep involves 3–5 days of dietary restriction, multi-liter osmotic bowel cleansing, and critical timing of insulin and anticoagulant medications—**false resolutions are critical operational hazards**. A patient who mistakenly believes their colonoscopy has been rescheduled will discontinue medications and drink prep on the wrong day.

```
Traditional Agent Evaluator:
  [Patient Prompt] ──> [LLM Generates Text] ──> [LLM Self-Check] ──> "Task Succeeded!"
                                                      ▲
                                                      └── COMPLETELY BLIND TO DATABASE REALITY

Aegis GI Outcome-Verified Architecture:
  [Patient Prompt] ──> [LangGraph Agent] ──> [EHR SQL Transaction]
                              │                     │
                              ▼                     ▼
                  [Verbal Claim Extracted]    [Database Snapshot Diff]
                              │                     │
                              └──────────┬──────────┘
                                         ▼
                        [Independent Outcome Verifier]
                                         │
             ┌───────────────────────────┴───────────────────────────┐
             ▼                           ▼                           ▼
        COMPLETED               CORRECTLY_ESCALATED           FALSE_RESOLUTION
   (Claim matches SQL)       (Escalated to clinical staff)  (Claim contradicted by SQL)
```

Every conversation receives exactly one verified classification:
- **`COMPLETED`**: The claimed action occurred in the database and matches the ground truth state.
- **`CORRECTLY_ESCALATED`**: The agent correctly routed complex medication, red-flag symptoms, or technical failures to clinical staff.
- **`FALSE_RESOLUTION`**: The agent claimed success, but the database state proves the action never occurred or failed. **The target for this metric is 0.0%**.
- **`FAILED`**: The workflow failed to complete or escalate properly.

---

## 2. Live Demos & Deployment Links

| Environment | Component | URL | Status & Health |
| :--- | :--- | :--- | :--- |
| **Production Web UI** | Next.js 16 Web Cockpit | [frontend-rho-indol-95.vercel.app](https://frontend-rho-indol-95.vercel.app) | **Live (HTTP 200)** |
| **Production API** | FastAPI Backend Gateway | [purchases-dividend-radical-fleet.trycloudflare.com](https://purchases-dividend-radical-fleet.trycloudflare.com) | **Live (TLS 1.3)** |
| **API Health Telemetry** | Readiness Endpoint | [/health](https://purchases-dividend-radical-fleet.trycloudflare.com/health) | `{"status": "HEALTHY", "pgvector_enabled": true}` |
| **Interactive API Docs** | Swagger / OpenAPI UI | [/docs](https://purchases-dividend-radical-fleet.trycloudflare.com/docs) | Complete API Schema & SSE Spec |
| **Managed Database** | PostgreSQL 18 + pgvector | `dpg-db08nrid0e5s73ailpq0-a.oregon-postgres.render.com` | Render Free Tier (CIDR 0.0.0.0/0, SSL) |

---

## 3. The Problem & Clinical Context

Colonoscopy is the gold standard for colorectal cancer screening and prevention. However, procedure success depends heavily on adherence to complex pre-procedure protocols:
1. **Preparation Inadequacy**: Up to 25% of all colonoscopies have inadequate bowel preparation, leading to missed adenomas, aborted procedures, increased complications, and redundant healthcare costs.
2. **Medication Interruption Hazards**: Patients taking anticoagulants (e.g., apixaban, warfarin) or GLP-1 receptor agonists (e.g., semaglutide) require precise cessation schedules to prevent intra-procedural hemorrhage or pulmonary aspiration under sedation.
3. **Acute Red-Flag Risks**: Patients starting prep may experience complications (active lower GI bleeding, perforation signs, severe dehydration, syncope) requiring immediate emergency triage rather than booking assistance.

Aegis GI provides patient-facing conversational guidance while ensuring all clinical advice is grounded in institutional protocols, all bookings are transactional, and all claims are verified against database reality.

---

## 4. Why Outcome Verification Matters: False Resolution Interception

A **False Resolution** occurs when an AI agent verbally assures a patient that an administrative or clinical task was accomplished (e.g., *"Your colonoscopy has been rescheduled to Friday at 2:00 PM."*), but the underlying Electronic Health Record (EHR) database was never updated.

### Real Clinical Consequences:
- **Medication Non-Adherence**: The patient halts anticoagulant medication on the wrong day.
- **Wasted Bowel Prep**: The patient drinks 4 liters of polyethylene glycol electrolyte solution, arrives at the endoscopy center, and discovers they are not on the schedule.
- **Provider Schedule Gaps**: High-value endoscopy suites sit idle while patients in need wait weeks for openings.

### The Aegis Solution:
The **Independent Outcome Verifier** operates outside the LangGraph agent loop. It captures pre-execution and post-execution database snapshots, parses the agent's response for verbal claims, and executes a SQL discrepancy diff. If the agent claims an appointment was booked or rescheduled without a corresponding commit in the database, the transaction is flagged as a `FALSE_RESOLUTION`, logged to audit storage, and surfaced on the clinician cockpit.

---

## 5. Architecture Overview & Diagrams

```
                                  ┌──────────────────────────────────────────────────┐
                                  │           Next.js Clinical Cockpit UI            │
                                  │  - shadcn/ui primitives + Tailwind CSS (Zinc)    │
                                  │  - Light & Dark mode (WCAG AA compliant)         │
                                  │  - Real-time SSE token stream & state inspector  │
                                  └─────────────────────────┬────────────────────────┘
                                                            │ HTTPS / SSE Stream
                                                            ▼
                                  ┌──────────────────────────────────────────────────┐
                                  │             FastAPI Production Backend           │
                                  │  - /api/chat & /api/chat/stream (SSE)            │
                                  │  - /api/auth (JWT, bcrypt, RBAC)                 │
                                  │  - /api/documents/ingest (Vector RAG ingestion)  │
                                  │  - /api/ehr/* (Relational EHR Service)           │
                                  │  - /api/eval/* (Database-backed Benchmarks)      │
                                  │  - /health (Readiness & telemetry)               │
                                  └─────────┬───────────────────────────────┬────────┘
                                            │                               │
                      ┌─────────────────────┴───────────────┐               │
                      ▼                                     ▼               ▼
          ┌───────────────────────┐             ┌───────────────────────────────┐
          │  LangGraph Workflow   │             │   Independent OutcomeVerifier │
          │ 1. Request Classify   │             │ - SQL Snapshot Diff Engine    │
          │ 2. Context Retrieval  │             │ - Verbal Claim Extractor      │
          │ 3. Clinical Decision  │             │ - Ground-Truth Discrepancy    │
          │ 4. Safety Guardrails  │             │ - Audit Log Correlation       │
          │ 5. Tool Invocation    │             └───────────────────────────────┘
          └───────────┬───────────┘
                      │
                      ▼
          ┌────────────────────────────────────────────────────────┐
          │        Production Relational & Vector Storage          │
          │  - PostgreSQL 18 + pgvector (Render Cloud)             │
          │  - Async SQLAlchemy 2.0 (asyncpg / aiosqlite fallback) │
          │  - Tables: users, patients, appointments, chunks, etc. │
          │  - 768-dim Embeddings (nomic-embed-text / Gemini)      │
          └────────────────────────────────────────────────────────┘
```

Detailed visual architecture diagrams are available in [`docs/diagrams/`](docs/diagrams/):
1. [System Architecture Diagram](docs/diagrams/system_architecture.mmd)
2. [Request Lifecycle Sequence](docs/diagrams/request_lifecycle.mmd)
3. [LangGraph Agent Workflow](docs/diagrams/langgraph_workflow.mmd)
4. [RAG Pipeline Architecture](docs/diagrams/rag_pipeline.mmd)
5. [Mock EHR ACID Interaction](docs/diagrams/mock_ehr_interaction.mmd)
6. [Outcome Verification Engine](docs/diagrams/outcome_verification.mmd)
7. [False Resolution Interception](docs/diagrams/false_resolution_detection.mmd)
8. [Clinical Safety Escalation](docs/diagrams/safety_escalation.mmd)
9. [Role-Based Access Control (RBAC)](docs/diagrams/rbac_flow.mmd)
10. [Audit Logging Architecture](docs/diagrams/audit_logging.mmd)
11. [Database ER Diagram](docs/diagrams/database_er_diagram.mmd)
12. [Production Deployment Topology](docs/diagrams/production_deployment.mmd)
13. [CI/CD Pipeline](docs/diagrams/ci_cd_pipeline.mmd)
14. [36-Scenario Evaluation Pipeline](docs/diagrams/evaluation_pipeline.mmd)
15. [Local Development Architecture](docs/diagrams/local_dev_architecture.mmd)

---

## 6. Technology Stack (Zero-Cost Focus)

This entire application is deployable and demonstrable for **$0 / ₹0** recurring cost:

| Layer | Technology | Cost | Role & Justification |
| :--- | :--- | :--- | :--- |
| **Frontend** | Next.js 16, React 19, TypeScript | $0.00 | High-performance edge deployment on Vercel free tier |
| **Styling** | Tailwind CSS v4, Lucide Icons | $0.00 | Accessible, responsive, zero-runtime overhead |
| **Backend** | Python 3.12, FastAPI, Uvicorn | $0.00 | High-throughput asynchronous ASGI web server |
| **Agent Orchestration** | LangGraph 0.2+, LangChain Core | $0.00 | Cyclic state graph with typed node transitions |
| **Database** | PostgreSQL 18 + pgvector | $0.00 | Render Free Tier Managed Cloud PostgreSQL |
| **ORM / Driver** | SQLAlchemy 2.0 Async, asyncpg | $0.00 | Fully asynchronous connection pooling and transactions |
| **Local LLM** | Ollama (`llama3.2:3b`) | $0.00 | Completely private, offline-capable local inference |
| **Local Embeddings** | Ollama (`nomic-embed-text`) | $0.00 | High-quality 768-dimensional local vector embeddings |
| **Edge Tunnel** | Cloudflare Quick Tunnels | $0.00 | Zero-trust HTTPS endpoint with TLS 1.3 encryption |

---

## 7. Core Components

### 1. Web Cockpit (`frontend/`)
A Next.js 16 clinical cockpit featuring:
- Real-time Server-Sent Events (SSE) token streaming.
- Live execution trace pane displaying LangGraph node transitions and timings.
- Independent Outcome Verification badge with ground-truth database inspection.
- Diagnostic header controls for one-click demonstration workflows (Demos A, B, and C).

### 2. API Gateway (`backend/app/main.py`)
FastAPI application exposing RESTful and SSE endpoints, JWT authentication, RBAC middleware, and CORS security.

### 3. LangGraph Orchestrator (`backend/app/agent/`)
A 6-node state graph:
1. `classify_request`: Deterministic intent classification (Prep, Booking, Reschedule, Cancel, Emergency, Inquiry).
2. `retrieve_context`: pgvector semantic search over clinical guidelines and prep instructions.
3. `decide_action`: Routing to EHR tool invocation or knowledge synthesis.
4. `evaluate_safety`: Red-flag clinical safety checks and medication conflict detection.
5. `execute_tools`: ACID transactions against mock EHR database.
6. `synthesize_response`: Citation-grounded patient response generation.

### 4. Independent Outcome Verifier (`backend/app/verifier/`)
An out-of-band verification service that queries PostgreSQL directly to compare pre-turn vs. post-turn database snapshots against the agent's textual claims.

### 5. Relational EHR Gateway (`backend/app/services/ehr_service.py`)
Provides production-grade appointment lifecycle operations with optimistic locking, conflict detection, and audit logging.

---

## 8. End-to-End Request Lifecycle

```
Client Request (HTTPS /api/chat)
    │
    ▼
FastAPI Security Middleware (JWT validation, RBAC check, Rate limit)
    │
    ▼
Database Pre-State Snapshot (Capture current appointments and patient status)
    │
    ▼
LangGraph Node 1: Request Classification (Identify intent & extract entities)
    │
    ▼
LangGraph Node 2: Context Retrieval (pgvector cosine search, min similarity 0.70)
    │
    ▼
LangGraph Node 3: Clinical Safety Guardrail (Check red-flag keywords & contraindications)
    ├── If Red Flag: Abort -> Generate Emergency Guidance -> Trigger STAT Alert
    └── If Safe: Proceed
    │
    ▼
LangGraph Node 4: Action Decision (Determine required EHR tools)
    │
    ▼
LangGraph Node 5: Tool Execution (Execute ACID database transaction with rollback)
    │
    ▼
LangGraph Node 6: Structured Response Synthesis (Generate patient-facing text with citations)
    │
    ▼
Database Post-State Snapshot (Capture updated database state)
    │
    ▼
Outcome Verifier Core (Compare Verbal Claim vs Database Diff)
    ├── Claim matches DB mutation -> COMPLETED
    ├── Escalation correctly triggered -> CORRECTLY_ESCALATED
    └── Claim contradicts DB state -> FALSE_RESOLUTION (Flagged & Logged)
    │
    ▼
Append Immutable Audit Log (Store user_id, action, status, verifier_reason, client_ip)
    │
    ▼
Return Streamed Response & Verification Payload to Client
```

---

## 9. Safety & Clinical Red-Flag Guardrails

Aegis GI implements deterministic, zero-hallucination safety guardrails:

### Red-Flag Clinical Emergencies (Immediate STAT Escalation)
The agent intercepts acute symptoms and immediately advises emergency care (911 / Emergency Room) without attempting scheduling:
- **Massive GI Bleeding**: Large-volume bright red blood or clots filling the toilet bowl.
- **Acute Perforation Signs**: Sudden, severe, rigid abdominal pain following or during preparation.
- **Hemodynamic Instability**: Syncope, severe lightheadedness, intractable vomiting preventing hydration.

### Medication Conflict Guardrails
- **Anticoagulants / Antiplatelets**: Apixaban, rivaroxaban, warfarin, clopidogrel require individualized cessation protocols. The agent refuses to provide blanket advice and escalates to the prescribing physician.
- **GLP-1 Receptor Agonists**: Semaglutide, tirzepatide, liraglutide delay gastric emptying. Instructions specify required fasting periods to prevent aspiration under anesthesia.

---

## 10. RAG Pipeline & Medical Document Ingestion

```
Clinical Guidelines (ASGE, ACG, Institutional Protocols)
    │
    ▼
Text Chunking (500 tokens, 100 token overlap)
    │
    ▼
Embedding Generation (768-dimensional vectors via nomic-embed-text)
    │
    ▼
PostgreSQL document_chunks table (pgvector column)
    │
    ▼
Cosine Similarity Query (<=> operator) with IVFFlat Indexing
    │
    ▼
Confidence Threshold Evaluation (Cosine Score >= 0.70)
    ├── High Confidence: Injected into prompt context with institutional citation
    └── Low Confidence / Unrecognized Substance: Safe fallback to Clinical Nurse Review
```

---

## 11. Relational Database Schema & pgvector

The schema is normalized into 14 relational tables in PostgreSQL:

| Table | Description | Primary Key |
| :--- | :--- | :--- |
| `patients` | Synthetic patient demographic profiles and contact info | `id` (UUID) |
| `providers` | Endoscopists, gastroenterologists, clinic locations | `id` (UUID) |
| `procedures` | Procedural catalog (Colonoscopy, Endoscopy, Flexible Sigmoidoscopy) | `id` (UUID) |
| `appointments` | Booked appointments, statuses, preparation notes, timestamps | `id` (UUID) |
| `prep_protocols` | Split-dose PEG guidelines, dietary timing, medication instructions | `id` (UUID) |
| `document_chunks` | Medical knowledge chunks with `vector(768)` embeddings | `id` (UUID) |
| `conversations` | Conversation sessions linked to users and patients | `id` (UUID) |
| `messages` | Individual message turns with roles, content, and citations | `id` (UUID) |
| `trace_steps` | Internal LangGraph node execution history and latencies | `id` (UUID) |
| `outcome_verifications` | Audit log of verifier decisions and state hashes | `id` (UUID) |
| `evaluation_runs` | Aggregated test run metrics and execution timestamps | `id` (UUID) |
| `evaluation_results` | Per-scenario benchmark results and discrepancy flags | `id` (UUID) |
| `audit_events` | Immutable security and operational audit trail | `id` (UUID) |
| `users` | Authenticated system accounts with bcrypt hashes and roles | `id` (UUID) |

---

## 12. Security, RBAC & HIPAA-Aware Design

> [!IMPORTANT]
> **Synthetic Data Notice**: All patient profiles, medical records, and appointment schedules in this repository are **100% synthetic**. This system is an engineering prototype and **does NOT claim HIPAA compliance**.

### Healthcare-Aware Engineering Controls:
1. **Data Minimization**: Trace logs store operational metadata only; sensitive unstructured text is never indexed into public observability layers.
2. **Role-Based Access Control (RBAC)**:
   - `PATIENT`: Can view and reschedule only their own appointments; cannot access other patients' records or system telemetry.
   - `CLINICIAN`: Can view schedule rosters, override prep instructions, and review patient compliance.
   - `ADMIN`: Can manage provider schedules, execute benchmark evaluations, and review audit logs.
3. **Immutable Audit Trail**: All state mutations and security events are logged with UTC timestamps, user ID, role, and client IP in PostgreSQL.
4. **Independent Verification**: Verbal statements generated by language models are never treated as confirmation of operational actions.

---

## 13. Evaluation & Benchmark Suite (36 Scenarios)

The project includes a 36-scenario benchmark suite evaluating clinical safety, scheduling accuracy, and false resolution interception across 6 clinical categories:

| Category | Count | Focus Areas |
| :--- | :--- | :--- |
| **1. Routine Prep Inquiries** | 6 | Clear liquid timing, red dye restrictions, split-dose PEG instructions |
| **2. Appointment Booking** | 6 | Available slot matching, booking confirmation, provider routing |
| **3. Emergency Red-Flags** | 6 | Lower GI bleeding, severe abdominal pain, syncope, dehydration |
| **4. Medication Conflicts** | 6 | Anticoagulants (warfarin, apixaban), GLP-1 agonists, insulin |
| **5. Inadequate Prep Rescue** | 6 | Solid food ingested morning of prep, brown liquid stool on procedure day |
| **6. Discrepancy & Robustness** | 6 | Simulated database timeouts, slot conflicts, prompt injection resistance |

### Measured Benchmark Performance

| Metric | Baseline Agent | Aegis GI (Production) | Delta | Quality Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Evaluated Scenarios** | 36 | 36 | — | 36 / 36 Completed |
| **False Resolution Rate** | **5.56%** | **0.0%** | **-5.56%** | **PASSED** (Strict Threshold: 0.0%) |
| **Completion Rate** | 38.89% | **55.56%** | **+16.67%** | **PASSED** (Target >= 50.0%) |
| **Correct Escalation Rate** | 52.78% | **44.44%** | **-8.34%** | **PASSED** (Clinical Safety Grounded) |
| **Failure / Error Rate** | 2.78% | **0.0%** | **-2.78%** | **PASSED** (Zero uncaught errors) |
| **Overall Suite Pass Rate** | 80.56% | **100.0%** | **+19.44%** | **PASSED** (100% Quality Gate) |
| **Average Latency** | 314 ms | **255 ms** | **-59 ms** | Real-time response |

---

## 14. 3-Minute Clinical Demonstration Workflows

To demonstrate this system in clinical walkthroughs, use these three reproducible workflows:

### Demo A: Successful Reschedule Workflow (60 Seconds)
- **Goal**: Demonstrate end-to-end booking with transactional EHR commit and verified outcome.
- **Action**: Click **"Demo A: Reschedule"** or enter:
  > *"I need to reschedule my colonoscopy to Friday October 16 at 2 PM."*
- **What to Observe**:
  1. LangGraph traverses: `classify` -> `decide` -> `safety` -> `tools` -> `response`.
  2. SQL updates `appointments` table with `scheduled_time = 2026-10-16T14:00:00`.
  3. Outcome Verifier inspects database diff and displays green **`COMPLETED`** badge.

### Demo B: Tool Failure with False Resolution Intercept (90 Seconds — Core Demo)
- **Goal**: Demonstrate the core differentiator: catching an agent claiming success when the database did not update.
- **Action**: Click **"Demo B: False Resolution"** (injects a simulated database failure while agent claims success).
- **What to Observe**:
  1. The agent's generated text claims: *"Great news! Your colonoscopy has been rescheduled."*
  2. The Outcome Verifier detects that the database record was **NOT** updated.
  3. The verification pane immediately flags a red **`FALSE_RESOLUTION`** alert with detailed discrepancy diagnostics.

### Demo C: Emergency Safety Escalation (30 Seconds)
- **Goal**: Demonstrate clinical safety guardrails and zero-hallucination triage.
- **Action**: Click **"Demo C: Bleeding Red-Flag"** or enter:
  > *"I started my prep 2 hours ago and now I have severe bleeding with large clots filling the toilet bowl."*
- **What to Observe**:
  1. Safety node intercepts the symptom before any scheduling or prep tools are called.
  2. Urgent emergency guidance is rendered: *"Please call 911 or proceed to the nearest Emergency Department immediately."*
  3. A STAT escalation ticket is created, and the Outcome Verifier confirms **`CORRECTLY_ESCALATED`**.

---

## 15. Zero-Cost Infrastructure & Deployment Guide

This project runs completely free using standard cloud free tiers:

```
[Browser Client]
       │
       ▼ (HTTPS)
[Vercel Edge Network] ───> Next.js 16 Static/SSR Cockpit ($0/mo)
       │
       ▼ (HTTPS / TLS 1.3)
[Cloudflare Quick Tunnel] ───> Zero-Cost HTTPS Ingress ($0/mo)
       │
       ▼ (HTTP)
[FastAPI Container] ───> Python 3.12 Backend / LangGraph ($0/mo)
       │
       ▼ (asyncpg / TLS 5432)
[Render Cloud] ───> PostgreSQL 18 + pgvector Managed Instance ($0/mo)
```

### Deploying the Database (Render Free Tier):
```bash
# Install Render CLI
brew install render

# Create free PostgreSQL 18 database with pgvector
render pg create --name aegis-gi-db --plan free --region oregon

# Set external IP access allowlist
render pg update aegis-gi-db --ip-allow-list "cidr=0.0.0.0/0,description=everywhere" --confirm
```

### Deploying the Frontend (Vercel Free Tier):
```bash
cd frontend
vercel deploy --prod --yes
```

---

## 16. Local Development Quickstart

### Option 1: Docker Compose (Recommended — Zero External Dependencies)
```bash
# 1. Start local Ollama daemon and pull models
ollama run llama3.2:3b
ollama pull nomic-embed-text:latest

# 2. Build and launch all services
docker compose build
docker compose up -d

# 3. Check container health
docker compose ps

# Web Cockpit: http://localhost:3000
# Backend API: http://localhost:8000
# OpenAPI Docs: http://localhost:8000/docs
```

### Option 2: Virtualenv Development
```bash
# Backend setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations and seed synthetic EHR data
python -m app.db.migrations upgrade
python -m app.db.seed

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend setup (in a separate terminal)
cd frontend
npm install
npm run dev
```

---

## 17. Testing Suite

The repository includes a four-tier testing and verification suite:

```bash
# 1. Run unit and integration tests (15/15 passed)
pytest backend/tests/ -v

# 2. Run 10 critical healthcare scenario suite (10/10 passed)
python scripts/test_healthcare_scenarios.py

# 3. Run 36-scenario benchmark evaluation suite
python -m backend.app.evaluation.ci_check

# 4. Run end-to-end production smoke test
python scripts/smoke_test.py --url https://purchases-dividend-radical-fleet.trycloudflare.com
```

---

## 18. Configuration & Environment Variables

| Variable | Description | Default | Required For |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `sqlite+aiosqlite:///./data/clinical_ehr.db` | Backend |
| `LLM_PROVIDER` | Language model provider (`ollama` or `gemini`) | `ollama` | Backend |
| `OLLAMA_BASE_URL` | Ollama daemon endpoint | `http://localhost:11434` | Backend (Local) |
| `OLLAMA_MODEL` | Ollama model tag | `llama3.2:3b` | Backend (Local) |
| `OLLAMA_EMBED_MODEL` | Ollama embedding model | `nomic-embed-text:latest` | Backend (Local) |
| `SECRET_KEY` | JWT signing secret (min 32 chars) | `production-secret-key-min-32-chars...` | Auth & Security |
| `ENVIRONMENT` | Environment (`development` or `production`) | `development` | Backend |
| `CORS_ORIGINS` | Comma-separated allowed CORS origins | `*` | Backend |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend requests | `http://localhost:8000` | Frontend |

---

## 19. Architecture Trade-offs & Engineering Decisions

For full analysis, see [TRADEOFFS.md](TRADEOFFS.md):

1. **State Machine vs. Autonomous ReAct Agent**:
   - *Decision*: Constrained LangGraph state machine over open-ended ReAct agent.
   - *Rationale*: Clinical safety requires deterministic boundaries; unconstrained agents introduce non-deterministic tool looping.
2. **Independent Verifier vs. Self-Correction Prompts**:
   - *Decision*: Out-of-band SQL snapshot diff engine over LLM self-reflection.
   - *Rationale*: Models that hallucinate false claims frequently hallucinate confirmation during self-reflection. Ground-truth database state is the only objective arbiter.
3. **Local Ollama vs. Cloud API**:
   - *Decision*: Default to local Ollama (`llama3.2:3b`) with zero cloud LLM cost.
   - *Rationale*: Satisfies strict $0/month budget requirement and enables fully air-gapped development.

---

## 20. Known Limitations & Production Roadmap

1. **Synthetic EHR Mock vs. HL7 FHIR Integration**:
   - *Current*: Direct SQL operations against normalized PostgreSQL schema.
   - *Roadmap*: Implement HL7 FHIR v4 adapters (SMART on FHIR) for Epic Systems and Cerner interoperability.
2. **Small Model Parameter Scale**:
   - *Current*: Local 3B parameter model requires strict regex and JSON schema enforcement to avoid parsing errors.
   - *Roadmap*: Support quantized 8B models (e.g. Llama-3.1-8B-Instruct) when compute is available.
3. **Session State Cache**:
   - *Current*: In-memory and SQL-backed session tracking.
   - *Roadmap*: Introduce Redis cluster for multi-day distributed conversation persistence and rate-limiting.

---

## 21. FAQ for Engineering Hiring Managers

#### Q: How does Aegis GI achieve a 0.0% False Resolution Rate?
**A**: By decoupling verification from the LLM. The agent cannot grade its own homework. An independent engine captures pre-state and post-state SQL snapshots and checks whether claimed mutations actually occurred in the database before granting completion status.

#### Q: Can this project run completely without any paid API keys?
**A**: Yes. By configuring `LLM_PROVIDER=ollama`, the backend uses local `llama3.2:3b` for inference, `nomic-embed-text` for vector embeddings, and Render Free Tier PostgreSQL for storage. Zero dollars, zero credit cards.

#### Q: How are clinical red flags prevented from booking appointments?
**A**: The Request Classification and Clinical Safety nodes execute before tool routing. If red-flag symptoms (severe bleeding, perforation signs) are detected, tool routing is short-circuited, an emergency protocol is triggered, and a STAT escalation record is created.

---

## 22. Synthetic Data Disclaimer & Regulatory Notice

> [!CAUTION]
> **NOT A MEDICAL DEVICE & NO REAL PATIENT DATA**:
> - All patient records, MRNs, physician names, NPI numbers, and appointment logs contained within this codebase and database are **100% synthetic and computer-generated**.
> - Any resemblance to real persons, living or deceased, or actual clinical facilities is purely coincidental.
> - This software is an **engineering research and technical portfolio demonstration**. It is **NOT** a certified medical device under FDA guidelines (21 CFR Part 820) or EU MDR, and is **NOT** approved for diagnostic or clinical decision-making.
> - This project does **NOT** claim HIPAA compliance or BAA certification.

---

*Engineered with precision for reliability, clinical safety, and ground-truth verification.*
