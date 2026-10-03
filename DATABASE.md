# Aegis GI — Database Architecture & Schema Specification (`DATABASE.md`)

## 1. Overview & Architectural Rationale

Aegis GI utilizes **PostgreSQL 16/18 with the native `pgvector` extension** as its unified relational and semantic data store.

### Why PostgreSQL?
1. **ACID Transactional Guarantees**: In clinical scheduling, double-booking and slot contention must be prevented with strict serializable isolation and row-level locking.
2. **Schema Rigor & Integrity**: Strong foreign key constraints between patients, appointments, providers, procedures, and audit events prevent orphaned clinical records.
3. **Unified Relational & Vector Queries**: By utilizing `pgvector`, clinical relational data (e.g. patient allergy histories and procedure prep protocols) and high-dimensional semantic embeddings reside within the same database engine, eliminating distributed transaction issues common with external vector databases like Pinecone or Weaviate.

---

## 2. Relational Schema & Entity-Relationship Details

### 2.1 Core Relational Tables

```sql
-- 1. USERS (Authentication & Role-Based Access Control)
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL DEFAULT 'PATIENT', -- 'PATIENT', 'CLINICIAN', 'ADMIN'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. PATIENTS (Synthetic Demographics & Clinical Context)
CREATE TABLE patients (
    id VARCHAR PRIMARY KEY,
    mrn VARCHAR UNIQUE NOT NULL,
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    dob VARCHAR NOT NULL,
    phone VARCHAR,
    email VARCHAR,
    medical_history JSONB, -- Allergies, active medications, chronic conditions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. PROVIDERS (Gastroenterologists & Endoscopists)
CREATE TABLE providers (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    specialty VARCHAR NOT NULL,
    npi VARCHAR UNIQUE,
    active BOOLEAN DEFAULT TRUE
);

-- 4. PROCEDURES (Endoscopy Catalog)
CREATE TABLE procedures (
    id VARCHAR PRIMARY KEY,
    code VARCHAR NOT NULL, -- CPT code (e.g., 45378 for Colonoscopy)
    name VARCHAR NOT NULL,
    default_duration_minutes INTEGER DEFAULT 60,
    requires_prep BOOLEAN DEFAULT TRUE,
    requires_sedation BOOLEAN DEFAULT TRUE,
    description TEXT
);

-- 5. APPOINTMENTS (System of Record for Scheduling)
CREATE TABLE appointments (
    id VARCHAR PRIMARY KEY,
    patient_id VARCHAR REFERENCES patients(id) ON DELETE CASCADE,
    provider_id VARCHAR REFERENCES providers(id),
    procedure_type VARCHAR NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'scheduled', -- 'scheduled', 'rescheduled', 'cancelled', 'available'
    location VARCHAR,
    notes TEXT,
    reschedule_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. PREP_PROTOCOLS (Institutional Clinical Guidelines)
CREATE TABLE prep_protocols (
    id VARCHAR PRIMARY KEY,
    procedure_type VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    clear_liquids_hours INTEGER NOT NULL DEFAULT 24,
    first_dose_hours INTEGER NOT NULL DEFAULT 14,
    second_dose_hours INTEGER NOT NULL DEFAULT 4,
    instructions_text TEXT NOT NULL
);

-- 7. KNOWLEDGE_CHUNKS (Semantic Knowledge Base with pgvector)
CREATE TABLE document_chunks (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    section VARCHAR NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768), -- Matches nomic-embed-text and text-embedding-004
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. AUDIT_EVENTS (Immutable Clinical Audit Trail)
CREATE TABLE audit_events (
    id VARCHAR PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR,
    event_type VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    resource VARCHAR NOT NULL,
    patient_id VARCHAR,
    details JSONB
);

-- 9. EVALUATION_RUNS & RESULTS (Automated Benchmark Metrics)
CREATE TABLE evaluation_runs (
    id VARCHAR PRIMARY KEY,
    run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    suite_name VARCHAR NOT NULL,
    total_scenarios INTEGER NOT NULL,
    completed_count INTEGER NOT NULL,
    correctly_escalated_count INTEGER NOT NULL,
    false_resolution_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    false_resolution_rate FLOAT NOT NULL,
    completion_rate FLOAT NOT NULL,
    correct_escalation_rate FLOAT NOT NULL,
    average_latency_ms FLOAT NOT NULL,
    is_baseline BOOLEAN DEFAULT FALSE
);

CREATE TABLE evaluation_results (
    id VARCHAR PRIMARY KEY,
    run_id VARCHAR REFERENCES evaluation_runs(id) ON DELETE CASCADE,
    scenario_id VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    user_prompt TEXT NOT NULL,
    expected_outcome VARCHAR NOT NULL,
    actual_outcome VARCHAR NOT NULL,
    classification VARCHAR NOT NULL,
    verification_reason TEXT,
    latency_ms FLOAT NOT NULL,
    discrepancy_detected BOOLEAN NOT NULL
);
```

---

## 3. Vector Storage & Semantic Search

The `document_chunks` table uses the native `vector(768)` data type.

### Cosine Distance Operator: `<=>`
Cosine distance is used to compare normalized embedding vectors:
$$\text{similarity} = 1 - (\mathbf{u} \cdot \mathbf{v})$$

In SQL:
```sql
SELECT id, title, section, content, 
       1 - (embedding <=> :query_vector) AS similarity
FROM document_chunks
WHERE 1 - (embedding <=> :query_vector) >= 0.50
ORDER BY embedding <=> :query_vector ASC
LIMIT 3;
```

---

## 4. Transaction Boundaries & EHR State Verification

### Transaction Safety
All booking, rescheduling, and cancellation operations run inside explicit database transactions:
```python
async with get_db_session() as session:
    # 1. Row-level check for slot collisions
    existing = await session.execute(stmt_collision)
    if existing:
        raise SlotUnavailableError(...)
    
    # 2. Mutate appointment state
    appt.scheduled_time = new_slot
    appt.status = "rescheduled"
    
    # 3. Insert immutable audit event
    session.add(audit_event)
    
    # 4. Atomic Commit
    await session.commit()
```

### Pre- and Post-Execution Snapshot Verification
The `OutcomeVerifier` takes atomic database snapshots before and after the LangGraph agent executes:
```python
before_snapshot = await ehr_service.take_snapshot_async()
# Agent executes LangGraph turn...
after_snapshot = await ehr_service.take_snapshot_async()

# Verifier calculates state diff
diff = compute_snapshot_diff(before_snapshot, after_snapshot)
verification = outcome_verifier.verify(agent_claim, diff)
```
If the agent claims success but `diff.modified_appointments` is empty or does not match the claimed timestamp, the verifier deterministically classifies the turn as **`FALSE_RESOLUTION`**.
