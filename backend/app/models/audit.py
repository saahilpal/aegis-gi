from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class UserRole(str, Enum):
    PATIENT = "PATIENT"
    STAFF = "STAFF"
    ADMIN = "ADMIN"

class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    role: UserRole
    action: str  # e.g., "READ_PATIENT_RECORD", "UPDATE_APPOINTMENT", "VIEW_PREP_PROTOCOL"
    resource_type: str  # e.g., "Patient", "Appointment", "PrepProtocol", "WorkflowEvent"
    resource_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: str = "SUCCESS"  # "SUCCESS", "DENIED", "FAILED", "NOT_FOUND"
    ip_address: Optional[str] = "127.0.0.1"
    details: Optional[str] = None  # Non-PHI metadata only!
