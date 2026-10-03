# Aegis GI — REST API Reference & OpenAPI Specification (`API.md`)

## 1. Base URLs & Authentication

- **Local Base URL**: `http://localhost:8000`
- **Production Base URL**: `https://purchases-dividend-radical-fleet.trycloudflare.com`
- **OpenAPI Swagger UI**: `/docs`
- **OpenAPI ReDoc**: `/redoc`

### Authentication Scheme
Protected endpoints require a standard Bearer Token in the `Authorization` header:
```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

---

## 2. Core Endpoints

### 2.1 System Health
`GET /health`
- **Description**: Returns operational health, database engine, pgvector status, and active model provider.
- **Response `200 OK`**:
```json
{
  "status": "HEALTHY",
  "service": "Outcome-Verified GI Prep & Booking Agent",
  "version": "1.0.0",
  "environment": "production",
  "database_engine": "PostgreSQL",
  "pgvector_enabled": true,
  "llm_provider": "ollama",
  "gemini_model": "gemini-2.5-flash"
}
```

---

### 2.2 Clinical Chat with Outcome Verification
`POST /api/chat`
- **Description**: Submits a patient message through the LangGraph workflow, executes tools, records EHR state diffs, and returns independent verification.
- **Request Body**:
```json
{
  "message": "Please reschedule my colonoscopy to Friday October 16 at 2 PM.",
  "patient_id": "P101",
  "user_role": "PATIENT",
  "conversation_id": "conv-test-101",
  "force_tool_failure": null,
  "force_agent_hallucination": false
}
```
- **Response `200 OK`**:
```json
{
  "conversation_id": "conv-test-101",
  "response_text": "Your appointment has been successfully rescheduled to 2026-10-16 14:00:00+00:00. Please review your prep guidelines 3 days prior.",
  "citations": [],
  "claimed_action": {
    "action_type": "RESCHEDULE_APPOINTMENT",
    "claimed_status": "SUCCESS",
    "statement": "Your appointment has been successfully rescheduled to 2026-10-16 14:00:00+00:00.",
    "target_date": "2026-10-16",
    "target_time": "14:00",
    "appointment_id": "APT-1001",
    "confidence": 1.0
  },
  "outcome_verification": {
    "classification": "COMPLETED",
    "expected_outcome": "Appointment rescheduled in EHR to requested slot",
    "actual_outcome": "Appointment scheduled_time changed to 2026-10-16 14:00:00+00:00",
    "reason": "COMPLETED: Requested rescheduling verified against ground truth EHR Database state.",
    "evidence": [
      {
        "source": "CLINICAL_EHR",
        "field": "scheduled_time",
        "claimed_value": "2026-10-16 14:00",
        "actual_value": "2026-10-16 14:00:00+00:00",
        "discrepancy": false,
        "details": "Verified appointment modified."
      }
    ],
    "discrepancy_detected": false
  },
  "trace_steps": [
    {
      "node_id": "NODE-CLASSIFICATION",
      "node_name": "Request Classification",
      "status": "COMPLETED",
      "latency_ms": 0.05,
      "input_summary": "Please reschedule my colonoscopy...",
      "output_summary": "Classified as 'RESCHEDULE'"
    }
  ],
  "total_latency_ms": 14.5
}
```

---

### 2.3 Server-Sent Events (SSE) Stream
`GET /api/chat/stream?message=...&patient_id=P101`
- **Description**: Streams intermediate node execution trace events and incremental response tokens to the client.
- **Event Types Emitted**:
  - `status`: `{ "status": "STARTING", "message": "Evaluating message..." }`
  - `trace`: Full `TraceStep` object upon node completion.
  - `token`: Individual generated text tokens.
  - `outcome`: The final `VerificationResult` from the OutcomeVerifier.
  - `done`: Final payload with total latency and citations.

---

### 2.4 Electronic Health Record (EHR) Endpoints
- `GET /api/ehr/snapshot`: Returns full relational state of appointments, active slots, and audit logs.
- `GET /api/ehr/appointments`: Lists active patient appointments.
- `GET /api/ehr/slots`: Lists available unbooked procedure slots.
- `POST /api/ehr/reset`: Resets the database to pristine baseline synthetic state.

---

### 2.5 Evaluation & Benchmark Endpoints
- `GET /api/eval/latest`: Returns latest baseline vs improved benchmark comparison from PostgreSQL.
- `POST /api/eval/comparison`: Executes the 36-scenario benchmark suite live and returns the delta report.
- `GET /api/eval/scenarios`: Returns list of all 36 test scenario definitions.
