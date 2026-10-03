#!/usr/bin/env python3
"""
Aegis GI - End-to-End Live Production Smoke Test Script

Validates the full lifecycle against a live deployed URL or local test environment:
1. System Health Check (/health)
2. User Authentication Registration & Login (/api/auth/register, /api/auth/login)
3. Authenticated Identity Verification (/api/auth/me)
4. Clinical Document & Protocol Ingestion (/api/documents/ingest)
5. Clinical Chat Workflow with Real LLM & Outcome Verification (/api/chat)
6. Real-Time Observability & Evaluation Dashboard Metrics (/api/eval/latest)

Usage:
  python scripts/smoke_test.py [--url http://localhost:8000]
"""

import sys
import uuid
import argparse
import requests
from datetime import datetime, timezone

def log(step: str, msg: str, success: bool = True):
    symbol = "✓" if success else "✗"
    print(f"[{symbol}] {step}: {msg}")

def run_smoke_test(base_url: str):
    base_url = base_url.rstrip("/")
    print("=" * 65)
    print(f"AEGIS GI PRODUCTION SMOKE TEST - Target: {base_url}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 65)

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    # 1. Health Check
    try:
        res = session.get(f"{base_url}/health", timeout=10)
        if res.status_code != 200:
            log("Health Check", f"Failed with status {res.status_code}: {res.text}", False)
            sys.exit(1)
        data = res.json()
        log("Health Check", f"Status: {data.get('status')}, Database: {data.get('database_engine')}, Vector: {data.get('pgvector_enabled')}")
    except Exception as e:
        log("Health Check", f"Network error connecting to {base_url}: {e}", False)
        sys.exit(1)

    # 2. Auth: Register
    unique_suffix = uuid.uuid4().hex[:6]
    test_email = f"smoketest_{unique_suffix}@aegisgi.health"
    test_password = f"P@ssword_{unique_suffix}!"
    try:
        reg_payload = {
            "email": test_email,
            "password": test_password,
            "full_name": f"QA Verifier {unique_suffix}",
            "role": "CLINICIAN"
        }
        res = session.post(f"{base_url}/api/auth/register", json=reg_payload, timeout=10)
        if res.status_code not in (200, 201):
            log("User Registration", f"Failed ({res.status_code}): {res.text}", False)
            sys.exit(1)
        user_info = res.json().get("user", {})
        log("User Registration", f"User created: {user_info.get('email')} (ID: {user_info.get('id')})")
    except Exception as e:
        log("User Registration", f"Error during registration: {e}", False)
        sys.exit(1)

    # 3. Auth: Login
    try:
        login_payload = {
            "email": test_email,
            "password": test_password
        }
        res = session.post(f"{base_url}/api/auth/login", json=login_payload, timeout=10)
        if res.status_code != 200:
            log("User Login", f"Failed ({res.status_code}): {res.text}", False)
            sys.exit(1)
        token_data = res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            log("User Login", "No access_token returned in response", False)
            sys.exit(1)
        session.headers.update({"Authorization": f"Bearer {access_token}"})
        log("User Login", f"JWT Bearer token acquired ({token_data.get('token_type')})")
    except Exception as e:
        log("User Login", f"Error during login: {e}", False)
        sys.exit(1)

    # 4. Auth: Profile Me
    try:
        res = session.get(f"{base_url}/api/auth/me", timeout=10)
        if res.status_code != 200:
            log("Auth Verification", f"Failed ({res.status_code}): {res.text}", False)
            sys.exit(1)
        me = res.json()
        log("Auth Verification", f"Authenticated as {me.get('full_name')} ({me.get('role')})")
    except Exception as e:
        log("Auth Verification", f"Error querying /api/auth/me: {e}", False)
        sys.exit(1)

    # 5. Ingestion: Upload Protocol Document
    try:
        doc_payload = {
            "title": f"Live Smoke Clinical Protocol {unique_suffix}",
            "source_file": "smoke_test_guideline.md",
            "section": "Preparation Guidelines",
            "content": (
                "Patients scheduled for morning colonoscopies must commence clear liquid intake "
                "24 hours prior to the procedure. Bowel cleansing with PEG split-dose solutions "
                "must be administered in two equal volumes: half 12 hours prior and the remaining "
                "half 5 hours prior to the scheduled appointment. Never mix prep with red dyes."
            )
        }
        res = session.post(f"{base_url}/api/documents/ingest", json=doc_payload, timeout=10)
        if res.status_code not in (200, 201):
            log("Document Ingestion", f"Failed ({res.status_code}): {res.text}", False)
            sys.exit(1)
        doc_res = res.json()
        log("Document Ingestion", f"Ingested chunk {doc_res.get('chunk_id')} with vector embeddings.")
    except Exception as e:
        log("Document Ingestion", f"Error during ingestion: {e}", False)
        sys.exit(1)

    # 6. Clinical Chat with Outcome Verification
    try:
        chat_payload = {
            "message": "When should I drink my second dose of colonoscopy prep solution?",
            "patient_id": "P101",
            "user_role": "PATIENT"
        }
        res = session.post(f"{base_url}/api/chat", json=chat_payload, timeout=20)
        if res.status_code != 200:
            log("Clinical Chat & Verification", f"Failed ({res.status_code}): {res.text}", False)
            sys.exit(1)
        chat_data = res.json()
        verification = chat_data.get("outcome_verification", {})
        classification = verification.get("classification")
        reason = verification.get("reason")
        trace = chat_data.get("trace_steps") or chat_data.get("trace", [])
        
        log(
            "Clinical Chat & Verification",
            f"Outcome: {classification} | Steps: {len(trace)} | Verified Reason: {str(reason)[:80]}..."
        )
    except Exception as e:
        log("Clinical Chat & Verification", f"Error during chat turn: {e}", False)
        sys.exit(1)

    # 7. Observability: Evaluation Dashboard Query
    try:
        res = session.get(f"{base_url}/api/eval/latest", timeout=10)
        if res.status_code != 200:
            log("Eval Dashboard", f"Failed ({res.status_code}): {res.text}", False)
            sys.exit(1)
        eval_data = res.json()
        baseline = eval_data.get("baseline") or eval_data.get("baseline_summary", {})
        improved = eval_data.get("improved") or eval_data.get("improved_summary", {})
        log(
            "Eval Dashboard",
            f"Baseline False Res: {baseline.get('false_resolution_rate', 'N/A')}% | "
            f"Improved False Res: {improved.get('false_resolution_rate', 'N/A')}%"
        )
    except Exception as e:
        log("Eval Dashboard", f"Error retrieving evaluation metrics: {e}", False)
        sys.exit(1)

    print("=" * 65)
    print("ALL PRODUCTION SMOKE TESTS PASSED SUCCESSFULLY! (0 Failures)")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis GI Live Smoke Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Target server URL (default: http://localhost:8000)")
    args = parser.parse_args()
    run_smoke_test(args.url)
