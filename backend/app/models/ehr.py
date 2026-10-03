from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Patient(BaseModel):
    id: str = Field(..., description="Unique patient identifier (e.g. P101)")
    mrn: str = Field(..., description="Medical Record Number (e.g. GI-89021)")
    first_name: str
    last_name: str
    dob: str
    gender: str
    phone: str
    email: str
    medical_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    portal_access: bool = True

class Provider(BaseModel):
    id: str
    name: str
    specialty: str = "Gastroenterology"
    npi: str
    active: bool = True

class Appointment(BaseModel):
    id: str
    patient_id: str
    provider_id: str
    procedure_type: str = "colonoscopy"
    scheduled_time: datetime
    duration_minutes: int = 60
    status: str = "scheduled"  # scheduled, rescheduled, cancelled, completed
    location: str = "Suite 400 - Endoscopy Suite A"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Procedure(BaseModel):
    id: str
    code: str
    name: str
    default_duration_minutes: int = 60
    requires_prep: bool = True
    requires_sedation: bool = True
    description: str

class PrepProtocol(BaseModel):
    id: str
    procedure_type: str
    title: str
    bowel_prep_type: str
    diet_rules: List[str]
    medication_rules: List[str]
    hydration_rules: List[str]
    last_intake_window_hours: int = 4

class WorkflowEvent(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str
    actor_role: str
    patient_id: Optional[str] = None
    appointment_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: str = "SUCCESS"
