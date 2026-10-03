# Aegis GI — Healthcare Safety Architecture & Clinical Boundaries (`SAFETY.md`)

## 1. System Scope & Clinical Boundaries

Aegis GI is explicitly designed and restricted to **administrative appointment coordination and patient bowel preparation education** for gastrointestinal endoscopy procedures.

### In-Scope Capabilities
- Rescheduling, booking, and cancelling routine screening and surveillance colonoscopies.
- Explaining dietary restrictions during preparation (e.g. clear liquid phase, avoiding red and purple food dyes).
- Providing split-dose polyethylene glycol (PEG-3350) ingestion timing based on procedure arrival time.
- Communicating institutional medication hold protocols (e.g. evening basal insulin dose reductions and anticoagulant cessation windows per gastroenterologist referral notes).
- Escalating patients to human triage nurses when symptoms or medical conditions fall outside established protocols.

### Out-of-Scope Capabilities (Strictly Intercepted)
- **Zero Medical Diagnosis**: The agent will never diagnose abdominal pain, gastrointestinal bleeding, ulcers, inflammatory bowel disease, or cancer.
- **Zero Prescription or Alteration of Treatment**: The agent will never prescribe medications, alter dosages outside institutional prep adjustment charts, or recommend off-label remedies.
- **Zero Triage of Acute Medical Emergencies**: Any emergent symptoms immediately trigger safety escalation and directives to emergency services (911).

---

## 2. Red-Flag Symptom Interception & Emergency Guardrails

Aegis GI implements deterministic, rule-based keyword and semantic safety guardrails in `backend/app/agent/safety.py` that evaluate patient utterances before any tool execution occurs.

### Emergency Categories & Clinical Actions

| Category | Indicative Symptoms / Triggers | Clinical Action | Output Urgency |
| :--- | :--- | :--- | :--- |
| **Severe GI Hemorrhage** | "Severe bleeding", "large clots", "blood in stool filling toilet bowl", "dark black tarry stool" | Direct patient to immediately halt prep, call 911, and proceed to nearest ER. | `EMERGENCY_911` |
| **Hemodynamic Compromise** | "Passed out", "fainted", "dizzy and clammy", "severe lightheadedness", "syncope" | Instruct patient to lie flat, call emergency services (911) immediately. | `EMERGENCY_911` |
| **Severe Abdominal Pain** | "10/10 pain", "unbearable cramps", "rigid abdomen", "severe acute pain" | Direct patient to stop prep immediately and contact clinical triage or visit ER. | `URGENT_PROVIDER` |
| **Anaphylaxis / Intolerance** | "Throat tightness", "difficulty breathing", "wheezing", "severe allergic hives" | Emergency anaphylaxis protocol: Halt prep, call 911. | `EMERGENCY_911` |
| **Severe Persistent Emesis** | "Vomiting every sip", "cannot keep down water for 4 hours" | Create urgent nurse ticket for antiemetic protocol or procedure postponement. | `CLINIC_STAFF` |

---

## 3. Human Escalation Protocol

When an emergency or protocol ambiguity is detected, the agent:
1. **Bypasses Operational Tools**: Schedulers and booking tools are completely disabled for the turn.
2. **Generates an Immutable Escalation Record**: Calls `create_human_escalation_async` with patient ID, urgency level (`EMERGENCY_911`, `URGENT_PROVIDER`, or `CLINIC_STAFF`), clinical context, and timestamp.
3. **Provides Deterministic Patient Guidance**: Delivers immediate, unambiguous safety instructions rather than probabilistic generated prose.
4. **Verifies Escalation Outcome**: The `OutcomeVerifier` verifies that an escalation event was recorded in the database, certifying the turn as **`CORRECTLY_ESCALATED`**.

---

## 4. Regulatory Disclaimer: Not a Medical Device

> [!CAUTION]
> **Regulatory Notice**: Aegis GI is an engineering research prototype and operational demonstration. It is **NOT an FDA-cleared Software as a Medical Device (SaMD)**, does not provide clinical diagnosis or therapeutic decision-making, and must never be deployed in real patient-care settings without rigorous clinical validation, human-in-the-loop oversight, and regulatory authorization.
