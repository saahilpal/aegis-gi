# Aegis GI — Technology Trade-Offs & Architectural Decisions (`TRADEOFFS.md`)

Every architectural decision in Aegis GI balances operational reliability, clinical safety, latency, cost, and developer experience. Below is the systematic documentation of all 11 core technical decisions.

---

## 1. Orchestration: LangGraph vs. Custom State Machine vs. Simple Function Routing

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Deterministic multi-step clinical routing with state persistence, trace inspection, and conditional tool execution. |
| **Options Evaluated** | 1. LangGraph Directed StateGraph<br>2. Custom Python State Machine (`enum` + `match-case`)<br>3. Simple sequential function routing |
| **Advantages of LangGraph** | Formal node/edge lifecycle, native async support (`ainvoke`), granular state schema (`AgentState`), structured trace generation per node, and direct compatibility with LangSmith observability. |
| **Disadvantages of LangGraph** | Additional library dependency; requires careful event loop management when mixing synchronous tooling with asyncpg database drivers. |
| **Final Decision** | **LangGraph**. Provides an industry-standard, auditable, node-by-node trace graph essential for clinical workflows. |

---

## 2. Relational Storage: PostgreSQL vs. MongoDB / Document Store

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | ACID transactional consistency for appointment slot allocation and relational foreign keys between patients, providers, and procedures. |
| **Options Evaluated** | 1. PostgreSQL (Relational + ACID)<br>2. MongoDB (NoSQL Document Store) |
| **Advantages of PostgreSQL** | Row-level locking prevents race-condition double bookings; strict foreign key constraints prevent orphaned appointment records; native `pgvector` extension allows relational and vector queries in one engine. |
| **Disadvantages of PostgreSQL** | Requires schema definitions and migrations rather than dynamic schemaless JSON ingestion. |
| **Final Decision** | **PostgreSQL**. Clinical scheduling requires strict ACID guarantees and transactional rollback on failure. |

---

## 3. Vector Database: pgvector vs. Dedicated Vector Stores (Pinecone / FAISS)

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Semantic search across institutional prep protocols and medication guidelines with zero infrastructure cost and zero operational fragmentation. |
| **Options Evaluated** | 1. `pgvector` inside PostgreSQL<br>2. Pinecone / Weaviate (Cloud Vector DB)<br>3. FAISS / Chroma (Local in-memory / file-based) |
| **Advantages of pgvector** | Zero extra cost ($0); eliminates network hops to external vector services; enables atomic JOINs between vector chunks and relational procedure tables; ACID transactions apply to embeddings. |
| **Disadvantages of pgvector** | In extremely large corpora (>50M vectors), dedicated distributed vector engines offer faster indexing, but clinical prep guidelines comprise thousands of chunks where pgvector is exceptionally fast (<5ms). |
| **Final Decision** | **pgvector**. Colocating clinical protocols with the relational system of record eliminates distributed transaction failure modes. |

---

## 4. LLM Runtime: Local Ollama vs. Cloud Hosted APIs

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Zero-cost development, offline capability, privacy preservation, and portability. |
| **Options Evaluated** | 1. Local Ollama (`llama3.2:3b`)<br>2. Cloud Hosted APIs (OpenAI / Anthropic / Gemini) |
| **Trade-Off Analysis** | Local models offer 100% privacy, zero token costs, and offline test execution, but smaller parameter models require structured extraction guardrails to prevent schema drift. Cloud models offer superior zero-shot nuance but introduce token fees and latency. |
| **Final Decision** | **Hybrid / Dual-Provider Architecture**. Primary local engine defaults to Ollama with configurable switch to cloud LLMs via `LLM_PROVIDER` environment variable. |

---

## 5. Frontend Hosting: Vercel vs. Self-Hosted Container

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Fast global edge delivery, automatic HTTPS, zero server maintenance, and $0 recurring cost. |
| **Options Evaluated** | 1. Vercel Hobby Tier (Edge Next.js)<br>2. Self-hosted Docker container on VPS |
| **Advantages of Vercel** | Native Next.js 16 optimization, automatic edge compression, free TLS certificates, instant git deployments, and zero operational overhead. |
| **Disadvantages of Vercel** | Serverless function timeout limits (10–15s), but client-side API calls route directly to the persistent backend API. |
| **Final Decision** | **Vercel**. Provides the fastest, most reliable zero-cost web deployment for Next.js. |

---

## 6. Container Orchestration: Docker Compose vs. Kubernetes (k8s)

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Simple, reproducible local and staging environment replicating the full multi-service topology. |
| **Options Evaluated** | 1. Docker Compose<br>2. Kubernetes (k8s / Minikube / Helm) |
| **Trade-Off Analysis** | Kubernetes adds immense operational complexity (ingress controllers, PVs, secrets manifests, control plane overhead) unnecessary for a multi-service clinical agent prototype. Docker Compose provides single-command setup (`docker compose up -d`) with identical container parity. |
| **Final Decision** | **Docker Compose**. Maximizes developer ergonomics and clinical demonstrability without artificial overhead. |

---

## 7. Real-Time Streaming: Server-Sent Events (SSE) vs. WebSockets

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Real-time token streaming from LLM and live node-by-node trace progress to the browser. |
| **Options Evaluated** | 1. Server-Sent Events (SSE) over HTTP/2<br>2. Full-duplex WebSockets |
| **Advantages of SSE** | Unidirectional client consumption aligns with agent generation; operates over standard HTTP/2 without connection upgrade issues; automatic reconnection handling; simpler firewall and proxy traversal. |
| **Disadvantages of SSE** | Does not support client-to-server multiplexing on the same socket (regular POST is used for messages). |
| **Final Decision** | **Server-Sent Events (SSE)**. Cleaner semantics for LLM response and trace streaming. |

---

## 8. Clinical System of Record: Relational Mock EHR vs. Real HL7 FHIR Integration

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Deterministic testing of appointment mutations, fault injection, and outcome verification without external hospital system dependencies. |
| **Options Evaluated** | 1. Relational Mock EHR in PostgreSQL<br>2. Live Hospital Epic/Cerner SMART on FHIR Sandbox |
| **Trade-Off Analysis** | Real FHIR sandboxes suffer from intermittent external downtime, rate limits, slow response times (>2s), and restrictive authentication renewals during demos. The relational mock EHR provides identical schema semantics, atomic rollbacks, and instant fault injection (`SLOT_UNAVAILABLE`, `API_TIMEOUT`). |
| **Final Decision** | **Relational Mock EHR**. Guarantees 100% deterministic, repeatable demonstration and testing while modeling real clinical database schemas. |

---

## 9. Safety System: Deterministic Rule Guardrails vs. LLM Safety Evaluator

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | 100% reliable interception of acute red-flag medical emergencies (e.g. severe bleeding, anaphylaxis, syncope). |
| **Options Evaluated** | 1. Deterministic keyword/pattern matching + clinical classification<br>2. LLM-as-a-judge safety prompting |
| **Trade-Off Analysis** | LLM safety classifiers are non-deterministic, subject to jailbreak prompt injections, and introduce 200–500ms of latency before emergency advice is rendered. Deterministic rule guardrails execute in <1ms with zero false negatives on known red-flag terms. |
| **Final Decision** | **Deterministic Rule Guardrails**. Life-safety clinical boundaries cannot rely on probabilistic model inference. |

---

## 10. Concurrency Model: Native Asynchronous (asyncpg) vs. Synchronous Threads

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | High-throughput non-blocking I/O across database queries, vector similarity searches, and LLM requests. |
| **Options Evaluated** | 1. Native `async/await` with `asyncpg` and SQLAlchemy async engine<br>2. Synchronous `psycopg2` running inside ThreadPoolExecutors |
| **Trade-Off Analysis** | Thread pools introduce event loop collisions in Python asyncio frameworks (`Task got Future attached to a different loop`). Native async coroutines share a single event loop per worker process, minimizing memory footprint and maximizing concurrency. |
| **Final Decision** | **Native Async**. Ensures stable event loop execution across LangGraph nodes and FastAPI endpoints. |

---

## 11. Verification Timing: Post-Execution Verification vs. Pre-Flight Speculation

| Dimension | Decision |
| :--- | :--- |
| **Requirement** | Eliminate false resolutions where the agent claims an action succeeded when the database write failed. |
| **Options Evaluated** | 1. Independent post-execution state verification (OutcomeVerifier)<br>2. Pre-execution speculative assumption (Agent claims output without verification) |
| **Trade-Off Analysis** | Pre-execution speculation is the primary cause of AI hallucination in healthcare. Independent post-execution verification inspects the actual database snapshot diff, guaranteeing the verbal claim is grounded in reality. |
| **Final Decision** | **Independent Post-Execution Verification**. The foundational differentiator of Aegis GI. |
