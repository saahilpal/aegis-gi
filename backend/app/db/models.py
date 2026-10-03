import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from .database import Base, is_sqlite

# Define Vector Column Type depending on dialect
if not is_sqlite:
    try:
        from pgvector.sqlalchemy import Vector
        VectorType = Vector(768)
    except ImportError:
        VectorType = JSON
else:
    VectorType = JSON

DateTimeTZ = DateTime(timezone=True)


class User(Base):
    """User account model for authentication and access control."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="PATIENT", nullable=False)  # PATIENT, CLINICIAN, ADMIN
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)


class Patient(Base):
    """Synthetic clinical patient record."""
    __tablename__ = "patients"

    id = Column(String(50), primary_key=True)  # e.g., P101
    mrn = Column(String(50), unique=True, nullable=False, index=True)  # e.g., GI-89021
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    dob = Column(String(20), nullable=False)  # YYYY-MM-DD
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    medical_history = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)

    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")


class Provider(Base):
    """Clinical healthcare provider."""
    __tablename__ = "providers"

    id = Column(String(50), primary_key=True)  # e.g., PR101
    name = Column(String(255), nullable=False)
    specialty = Column(String(255), nullable=False)
    npi = Column(String(20), nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    appointments = relationship("Appointment", back_populates="provider")


class Procedure(Base):
    """GI and Endoscopy procedure catalog."""
    __tablename__ = "procedures"

    id = Column(String(50), primary_key=True)  # e.g., PROC-COLON
    code = Column(String(20), nullable=False)   # CPT code e.g. 45378
    name = Column(String(255), nullable=False)
    default_duration_minutes = Column(Integer, default=60, nullable=False)
    requires_prep = Column(Boolean, default=True, nullable=False)
    requires_sedation = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=False)


class Appointment(Base):
    """Patient procedure appointment record in EHR."""
    __tablename__ = "appointments"

    id = Column(String(50), primary_key=True)  # e.g., APT-1001
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    provider_id = Column(String(50), ForeignKey("providers.id"), nullable=False)
    procedure_type = Column(String(100), nullable=False)
    scheduled_time = Column(DateTimeTZ, nullable=False, index=True)
    status = Column(String(50), default="scheduled", nullable=False)  # scheduled, rescheduled, cancelled, completed
    location = Column(String(255), default="Main Endoscopy Suite - Room 3", nullable=False)
    notes = Column(Text, nullable=True)
    reschedule_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    patient = relationship("Patient", back_populates="appointments")
    provider = relationship("Provider", back_populates="appointments")


class PrepProtocol(Base):
    """Bowel preparation and medication management protocol."""
    __tablename__ = "prep_protocols"

    id = Column(String(50), primary_key=True)  # e.g., PREP-PEG-SPLIT
    procedure_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    clear_liquids_hours = Column(Integer, default=24, nullable=False)
    first_dose_hours = Column(Integer, default=14, nullable=False)
    second_dose_hours = Column(Integer, default=4, nullable=False)
    instructions_text = Column(Text, nullable=False)


class DocumentChunk(Base):
    """Clinical guideline chunk with vector embedding for pgvector retrieval."""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    source_file = Column(String(255), nullable=False)
    section = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(VectorType, nullable=True)
    created_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)


class Conversation(Base):
    """Chat session conversation."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(50), default="P101", nullable=False)
    user_id = Column(String(36), nullable=True)
    created_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Message item inside conversation."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list, nullable=False)
    is_emergency = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class TraceStep(Base):
    """Telemetry trace step for LangGraph execution nodes."""
    __tablename__ = "trace_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), nullable=False, index=True)
    message_id = Column(String(36), nullable=True)
    node_id = Column(String(100), nullable=False)
    node_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    created_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)


class OutcomeVerification(Base):
    """Independent outcome verification record comparing claims to EHR ground truth."""
    __tablename__ = "outcome_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), nullable=False, index=True)
    message_id = Column(String(36), nullable=True)
    classification = Column(String(50), nullable=False)  # COMPLETED, CORRECTLY_ESCALATED, FALSE_RESOLUTION, FAILED
    expected_outcome = Column(Text, nullable=False)
    actual_outcome = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    evidence = Column(JSON, default=list, nullable=False)
    discrepancy_detected = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)


class EvaluationRun(Base):
    """Persistent benchmark evaluation execution suite run."""
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_timestamp = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)
    suite_name = Column(String(100), default="36_SCENARIO_CI_BENCHMARK", nullable=False)
    total_scenarios = Column(Integer, nullable=False)
    completed_count = Column(Integer, nullable=False)
    correctly_escalated_count = Column(Integer, nullable=False)
    false_resolution_count = Column(Integer, nullable=False)
    failed_count = Column(Integer, nullable=False)
    false_resolution_rate = Column(Float, nullable=False)
    completion_rate = Column(Float, nullable=False)
    correct_escalation_rate = Column(Float, nullable=False)
    average_latency_ms = Column(Float, nullable=False)
    is_baseline = Column(Boolean, default=False, nullable=False)

    results = relationship("EvaluationResult", back_populates="run", cascade="all, delete-orphan")


class EvaluationResult(Base):
    """Individual scenario execution outcome inside an evaluation run."""
    __tablename__ = "evaluation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("evaluation_runs.id"), nullable=False, index=True)
    scenario_id = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    user_prompt = Column(Text, nullable=False)
    expected_outcome = Column(Text, nullable=False)
    actual_outcome = Column(Text, nullable=False)
    classification = Column(String(50), nullable=False)
    verification_reason = Column(Text, nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    discrepancy_detected = Column(Boolean, default=False, nullable=False)

    run = relationship("EvaluationRun", back_populates="results")


class AuditEvent(Base):
    """HIPAA and clinical workflow audit logging."""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTimeTZ, default=lambda: datetime.now(timezone.utc), nullable=False)
    event_type = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=True)
    patient_id = Column(String(100), nullable=True)
    action = Column(String(255), nullable=False)
    resource = Column(String(255), nullable=False)
    details = Column(JSON, default=dict, nullable=False)
