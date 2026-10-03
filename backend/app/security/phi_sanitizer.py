import re
import logging
from typing import Dict, Any

# Regular expressions for common PHI patterns
PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "PHONE": r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.]?\d{3}[-.]?\d{4}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "DOB": r"\b(?:DOB|dob|Date of Birth|Birthdate)[:\s]+(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b",
    "MRN": r"\b(?:MRN|mrn|Medical Record Number)[:\s#]+[A-Z0-9-]{5,12}\b"
}

logger = logging.getLogger("phi_sanitizer")

def sanitize_phi(text: str) -> str:
    """
    Scrub raw PHI from free-text for safe application logging.
    Replaces sensitive identifiers with masked tokens.
    """
    if not text:
        return text

    sanitized = text
    for phi_type, pattern in PATTERNS.items():
        sanitized = re.sub(pattern, f"[REDACTED_{phi_type}]", sanitized, flags=re.IGNORECASE)
    
    return sanitized

def safe_log_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a sanitized copy of a dictionary, stripping or redacting PHI fields.
    """
    sanitized: Dict[str, Any] = {}
    sensitive_keys = {"patient_name", "first_name", "last_name", "phone", "email", "dob", "ssn", "allergies"}
    
    for k, v in payload.items():
        if k.lower() in sensitive_keys:
            sanitized[k] = "[REDACTED_PHI]"
        elif isinstance(v, str):
            sanitized[k] = sanitize_phi(v)
        elif isinstance(v, dict):
            sanitized[k] = safe_log_payload(v)
        else:
            sanitized[k] = v
            
    return sanitized
