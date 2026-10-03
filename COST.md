# Aegis GI — Zero-Cost Architecture & Budget Audit (`COST.md`)

## 1. Zero-Cost Principle & Commitment

The **Aegis GI** project is strictly engineered to operate at **₹0 / $0 recurring cost** across local development, containerized testing, continuous integration, database storage, and production hosting.

No component introduces mandatory billing, paid subscriptions, paid API keys, paid vector databases, or credit card requirements.

---

## 2. Infrastructure & Service Cost Audit

| Component | Selected Service / Tool | Cost | Free Limit / Tier Conditions | Credit Card / Billing Required? | Hard Requirement? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend Hosting** | **Vercel Hobby Tier** | **$0** | Unlimited deployments, 100 GB bandwidth/mo, free `*.vercel.app` domains | No | Yes |
| **Backend API Gateway** | **Render Free Tier / Cloudflare Quick Tunnel** | **$0** | 750 free instance hours/month on Render; unlimited encrypted ingress via Cloudflare | No | Yes |
| **Relational Database** | **Render PostgreSQL / Local PostgreSQL** | **$0** | 1 GB storage, 100 concurrent connections, PostgreSQL 16/18 with extensions | No | Yes |
| **Vector Search Engine** | **pgvector (Open Source)** | **$0** | Native PostgreSQL extension, zero external licensing fees, 768-dim HNSW/IVFFlat | No | Yes |
| **Local LLM Engine** | **Ollama (`llama3.2:3b`)** | **$0** | 100% offline, local GPU/CPU compute, zero API tokens or metering | No | Yes (for local dev) |
| **Local Embeddings** | **Ollama (`nomic-embed-text`)** | **$0** | 100% offline, 768-dim vector embeddings, zero API costs | No | Yes (for local dev) |
| **Cloud LLM (Optional)** | **Google Gemini Flash (Free Tier)** | **$0** | 15 RPM, 1 million TPM, 1,500 RPD free tier on Google AI Studio | No | No (Ollama is primary) |
| **CI / CD Quality Gate** | **GitHub Actions** | **$0** | 2,000 free runner minutes/month for public repositories | No | Yes |
| **Authentication & RBAC** | **FastAPI JWT + Passlib bcrypt** | **$0** | Self-hosted cryptographic tokens, zero third-party auth provider fees | No | Yes |
| **Audit Logging** | **PostgreSQL `audit_events` Table** | **$0** | Relational ACID logging, zero third-party observability subscriptions | No | Yes |
| **Domain & SSL/TLS** | **Vercel & Cloudflare Edge SSL** | **$0** | Automatic Let's Encrypt / Cloudflare certificates, zero domain purchase fees | No | Yes |
| **Mock EHR System** | **Relational ACID Database** | **$0** | Built into PostgreSQL schema, zero external EHR gateway subscription fees | No | Yes |

---

## 3. Cost Safety Guardrails & Prevention of Accidental Charges

To guarantee that the application can never accidentally incur financial liability, the following technical constraints are enforced in code:

1. **No External Paid API Fallbacks**: The LLM client in `backend/app/agent/llm.py` defaults strictly to `http://localhost:11434` (Ollama). If an external API key is absent or invalid, the system falls back to deterministic structured response synthesis rather than invoking paid third-party APIs.
2. **Context Window Clamping**: User inputs are clamped to a maximum of 1,000 characters and RAG document context is bounded to the top 3 chunks (max 1,500 tokens), preventing excessive prompt size.
3. **Database Resource Quotas**: Connection pools are configured with `pool_size=5, max_overflow=10` to remain well within free-tier connection limits on Render and Supabase.
4. **Synthetic Data Minimization**: Total database storage footprint for the complete clinical scenario suite, patients, appointments, and guideline vectors is less than **5 MB**, fitting easily within Render's 1 GB free allocation (0.5% utilization).
5. **Rate Limiting & Timeouts**: HTTP client requests to local and remote models enforce a strict 15.0-second timeout to prevent runaway hanging requests.
