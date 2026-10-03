# Aegis GI — Security Architecture & HIPAA-Aware Engineering (`SECURITY.md`)

> [!CAUTION]
> **Medical Disclaimer & Educational Use Only**:
> This software is an educational prototype and technology demonstration. It is NOT FDA-approved, CE-marked, or certified as a medical device (SaMD). It must NOT be used for real clinical diagnosis, treatment decisions, or emergency medical triage without qualified human physician supervision. All patient data, clinical records, and schedules in this repository are synthetic.

## 1. What This Project Does NOT Claim

> [!IMPORTANT]
> **Definitive Legal Disclaimer**: Aegis GI **DOES NOT claim HIPAA compliance**, HITECH certification, SOC 2 Type II certification, or HITRUST CSF attestation.
> 
> HIPAA compliance is an organizational, physical, legal, and operational certification covering signed Business Associate Agreements (BAAs), designated record sets, administrative safeguards, and business operations. A technical prototype cannot be "HIPAA compliant" in isolation.

Instead, Aegis GI demonstrates **HIPAA-Aware Engineering Practices** designed to model production healthcare security principles.

---

## 2. 100% Synthetic Patient Data

All clinical records, demographics, and procedure histories in this codebase are **100% synthetic**.

| Synthetic Profile | Identifier | Demographics | Clinical Context |
| :--- | :--- | :--- | :--- |
| **Sarah Lin** | `P101` / `GI-89021` | 52yo Female (DOB: 1974-05-14) | Routine 5-year surveillance colonoscopy; Split-dose PEG prep. |
| **Robert Taylor** | `P102` / `GI-44219` | 61yo Male (DOB: 1962-11-28) | Atrial fibrillation; holds Eliquis 48h prior; Lantus insulin dose adjustment. |
| **Emily Chen** | `P103` / `GI-77302` | 45yo Female (DOB: 1988-03-05) | Mild Crohn's Disease, iron deficiency; codeine allergy; morning EGD. |

No Protected Health Information (PHI), real patient identifiers, or genuine hospital records exist in this repository.

---

## 3. HIPAA-Aware Engineering Controls

### 3.1 Authentication & Role-Based Access Control (RBAC)
- **Token Format**: Standard JSON Web Tokens (JWT) signed with SHA-256 HMAC (`HS256`).
- **Password Hashing**: Cryptographic salt and hash utilizing `passlib[bcrypt]` with minimum work factor of 12.
- **Roles Defined**:
  - `PATIENT`: Strictly restricted to viewing and scheduling their own active appointments. Cross-patient lookups trigger access violation intercepts and security escalation.
  - `CLINICIAN`: Authorized to view assigned patient schedules, review preparation status, and handle triage escalation tickets.
  - `ADMIN`: Authorized to configure practice providers, procedure catalogs, institutional prep guidelines, and view benchmark analytics.

### 3.2 Authorization Interception Flow
Before any scheduling tool or data query executes in `backend/app/agent/graph.py`:
```python
is_auth, auth_msg = verify_tool_authorization(user_role, "cross_patient_access", patient_id, target_patient_id)
if not is_auth:
    # 1. Block tool execution immediately
    # 2. Log security alert to audit_events
    # 3. Create security ticket for clinic coordinator
    return {"error": "ACCESS_DENIED", "message": auth_msg}
```

### 3.3 Data Minimization & PHI-Aware Logging
- **Log Scrubbing**: Log outputs in `backend/app/main.py` and LangGraph trace steps summarize operations without dumping full patient clinical narratives or demographic blocks.
- **Zero Raw PII Exposure**: Telemetry only transmits necessary operational identifiers (e.g., appointment ID `APT-1001`, target timestamp `2026-10-16 14:00`).

### 3.4 Immutable Clinical Audit Logging
Every appointment booking, rescheduling, cancellation, failure, and escalation generates an immutable record in the `audit_events` relational table with:
- Global UUID (`AUD-xxxxxxxx`)
- Actor ID and role
- Event type and clinical action
- Resource URI (`Appointment/APT-1001` or `Escalation/ESC-xxxxxxxx`)
- Contextual details (new slot, reason, or failure code)
- UTC timestamp with timezone

---

## 4. Secret Management & Secure Configuration

- **Zero Hardcoded Secrets**: Secrets such as `SECRET_KEY`, `DATABASE_URL`, and API tokens are loaded strictly via environment variables.
- **Git Hygiene**: `.gitignore` explicitly filters out `.env`, `.env.local`, `*.db`, `*.sqlite`, and deployment metadata folders.
- **Transport Security**: All external communication (Vercel frontend and Render backend) enforces HTTPS with TLS 1.3 encryption in transit.
