# Aegis GI — Production Deployment Guide (`DEPLOYMENT.md`)

## 1. Zero-Cost Production Architecture Overview

The production topology separates concerns across specialized zero-cost tiers:
- **Frontend Client**: Next.js 16 deployed on **Vercel Hobby Tier** with global edge CDN caching.
- **Backend API Gateway**: FastAPI (Python 3.12) running with Uvicorn, exposed over public HTTPS with TLS 1.3.
- **Relational & Vector Storage**: **PostgreSQL 16/18 with native `pgvector`** deployed on Render Free Tier / containerized PostgreSQL.
- **Continuous Integration**: GitHub Actions running automated unit tests and CI evaluation gates on every pull request.

---

## 2. Environment Variables & Secret Configuration

Create a `.env` file in the root directory (based on `.env.example`):

```bash
# Service Metadata
ENVIRONMENT="production"
LOG_LEVEL="INFO"
PROJECT_NAME="Outcome-Verified GI Prep & Booking Agent"
VERSION="1.0.0"

# Database Configuration (Render PostgreSQL with pgvector)
DATABASE_URL="postgresql+asyncpg://aegis_db_5eua_user:<PASSWORD>@dpg-db08nrid0e5s73ailpq0-a.oregon-postgres.render.com:5432/aegis_db_5eua?ssl=require"
USE_PGVECTOR="true"

# LLM Runtime Configuration
LLM_PROVIDER="ollama" # "ollama" for local/containerized, "gemini" for cloud
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.2:3b"
OLLAMA_EMBED_MODEL="nomic-embed-text:latest"

# Cloud LLM Option (Optional - Free Tier)
GEMINI_API_KEY=""
GEMINI_MODEL="gemini-2.5-flash"

# Security & Cryptographic Tokens
SECRET_KEY="replace-with-a-64-character-cryptographically-secure-random-key"
ALGORITHM="HS256"

# Frontend Integration
NEXT_PUBLIC_API_URL="https://aegis-gi-backend.onrender.com"
```

---

## 3. Database Initialization & Automated Schema Setup

1. **Verify Database Connectivity**:
   ```bash
   python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('$DATABASE_URL', ssl='require'))"
   ```
2. **Apply Extensions and Seed Synthetic Data**:
   ```bash
   python -m backend.app.db.seed
   ```
   This script automates:
   - Verification of `vector` extension (`CREATE EXTENSION IF NOT EXISTS vector;`)
   - Creation of all relational tables (`users`, `patients`, `appointments`, `audit_events`, etc.)
   - Generation of 768-dimensional embeddings for institutional guidelines
   - Population of baseline appointments for synthetic patients (`P101`, `P102`, `P103`).

---

## 4. Frontend Deployment on Vercel (Free Tier)

The frontend is deployed to Vercel's zero-cost hobby tier:

```bash
cd frontend
# 1. Ensure production backend API URL is configured:
echo "NEXT_PUBLIC_API_URL=https://aegis-gi-backend.onrender.com" > .env.production

# 2. Deploy directly to production without interactive prompts:
vercel deploy --prod --yes
```

**Live Production URL**: [https://frontend-rho-indol-95.vercel.app](https://frontend-rho-indol-95.vercel.app)

---

## 5. Automated Production Smoke Testing

Execute the automated end-to-end smoke test against the live production deployment:

```bash
python scripts/smoke_test.py --url https://aegis-gi-backend.onrender.com
```

The smoke test verifies 7 critical production subsystems:
1. `[✓]` Health check readiness (`/health`)
2. `[✓]` User registration with bcrypt hashing (`/api/auth/register`)
3. `[✓]` JWT bearer token acquisition (`/api/auth/login`)
4. `[✓]` Authenticated RBAC verification (`/api/auth/me`)
5. `[✓]` Clinical protocol chunk ingestion into pgvector (`/api/documents/ingest`)
6. `[✓]` Clinical chat execution through LangGraph with Outcome Verification (`/api/chat`)
7. `[✓]` Evaluation metrics query from live PostgreSQL (`/api/eval/latest`)

---

## 6. Rollback Procedure

- **Frontend Rollback**:
  ```bash
  vercel rollback [DEPLOYMENT_ID]
  ```
- **Backend Rollback**:
  Restart backend service pointing to the previous git commit SHA or stable container image.
- **Database Rollback**:
  Reset database to clean baseline at any time:
  ```bash
  curl -X POST https://aegis-gi-backend.onrender.com/api/ehr/reset
  ```
