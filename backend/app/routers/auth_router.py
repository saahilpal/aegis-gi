import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select

from ..db.database import get_db_session
from ..db.models import User as UserModel
from ..security.auth import hash_password, verify_password, create_access_token, get_current_user_payload
from ..security.rate_limiter import enforce_rate_limit

router = APIRouter(prefix="/api/auth", tags=["Authentication & Access"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100)
    role: Optional[str] = Field("PATIENT", description="Requested role (PATIENT, CLINICIAN, STAFF)")

    @field_validator("role")
    @classmethod
    def sanitize_role(cls, v: Optional[str]) -> str:
        role = (v or "PATIENT").upper().strip()
        # Security: Prevent public self-escalation to ADMIN
        if role == "ADMIN":
            raise ValueError("Direct self-registration as ADMIN is prohibited. Contact system administrator.")
        if role not in ("PATIENT", "CLINICIAN", "STAFF"):
            raise ValueError("Role must be one of: PATIENT, CLINICIAN, STAFF.")
        return role

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request):
    """Register a new user account with hashed password in database."""
    enforce_rate_limit(request, max_requests=10, window_seconds=60, operation="auth_register")

    async with get_db_session() as session:
        stmt = select(UserModel).where(UserModel.email == req.email.lower().strip())
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists."
            )

        user_id = str(uuid.uuid4())
        hashed = hash_password(req.password)
        new_user = UserModel(
            id=user_id,
            email=req.email.lower().strip(),
            hashed_password=hashed,
            full_name=req.full_name,
            role=req.role,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(new_user)
        await session.commit()

        token = create_access_token({
            "sub": user_id,
            "email": new_user.email,
            "role": new_user.role,
            "name": new_user.full_name,
            "patient_id": user_id if new_user.role == "PATIENT" else None
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "role": new_user.role
            }
        }

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, request: Request):
    """Authenticate credentials against database and issue JWT."""
    enforce_rate_limit(request, max_requests=20, window_seconds=60, operation="auth_login")

    async with get_db_session() as session:
        stmt = select(UserModel).where(UserModel.email == req.email.lower().strip())
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        token = create_access_token({
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.full_name,
            "patient_id": user.id if user.role == "PATIENT" else None
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        }

@router.get("/me")
async def get_current_user(
    request: Request,
    payload: Dict[str, Any] = Depends(get_current_user_payload)
):
    """Fetch profile of current authenticated user from database."""
    enforce_rate_limit(request, max_requests=60, window_seconds=60, operation="auth_me")
    user_id = payload.get("sub")
    async with get_db_session() as session:
        user = await session.get(UserModel, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User account not found.")

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
