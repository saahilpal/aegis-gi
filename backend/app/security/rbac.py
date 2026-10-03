from typing import List, Union, Tuple, Optional
from fastapi import HTTPException, status
from ..models.audit import UserRole

# Operation permission matrix
PERMISSIONS = {
    UserRole.PATIENT: [
        "VIEW_OWN_PROFILE",
        "VIEW_OWN_APPOINTMENTS",
        "SEARCH_AVAILABLE_SLOTS",
        "BOOK_OWN_APPOINTMENT",
        "RESCHEDULE_OWN_APPOINTMENT",
        "CANCEL_OWN_APPOINTMENT",
        "QUERY_PREP_PROTOCOL",
        "REQUEST_HUMAN_ESCALATION"
    ],
    UserRole.STAFF: [
        "VIEW_OWN_PROFILE",
        "VIEW_ALL_PATIENTS",
        "VIEW_ALL_APPOINTMENTS",
        "SEARCH_AVAILABLE_SLOTS",
        "BOOK_ANY_APPOINTMENT",
        "RESCHEDULE_ANY_APPOINTMENT",
        "CANCEL_ANY_APPOINTMENT",
        "QUERY_PREP_PROTOCOL",
        "MANAGE_HUMAN_ESCALATION",
        "VIEW_AUDIT_LOGS"
    ],
    UserRole.ADMIN: [
        "*"  # Full administrative access
    ]
}

def _normalize_role(role: Union[UserRole, str]) -> UserRole:
    if isinstance(role, UserRole):
        return role
    try:
        return UserRole(role.upper())
    except Exception:
        return UserRole.PATIENT

def check_permission(role: Union[UserRole, str], required_permission: str) -> bool:
    """Check if role holds the required permission without throwing exceptions."""
    norm_role = _normalize_role(role)
    allowed_list = PERMISSIONS.get(norm_role, [])
    if "*" in allowed_list or required_permission in allowed_list:
        return True
    return False

def verify_permission(role: Union[UserRole, str], required_permission: str) -> bool:
    """Enforce RBAC permissions. Raises 403 Forbidden if role lacks permission."""
    if check_permission(role, required_permission):
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access Denied: Role '{role}' lacks required permission '{required_permission}'."
    )

def verify_tool_authorization(
    role: Union[UserRole, str],
    action: str,
    requester_id: str,
    target_patient_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Verify authorization before tool execution.
    Prevents patients from executing staff/admin operations or modifying other patient charts.
    """
    norm_role = _normalize_role(role)
    
    # 1. Cross-patient boundary check for patients
    if norm_role == UserRole.PATIENT:
        if target_patient_id and target_patient_id != requester_id:
            return False, f"Unauthorized: Patient {requester_id} cannot access or modify records for patient {target_patient_id}."

        # Map action to patient permission
        permission_map = {
            "book_appointment": "BOOK_OWN_APPOINTMENT",
            "reschedule_appointment": "RESCHEDULE_OWN_APPOINTMENT",
            "cancel_appointment": "CANCEL_OWN_APPOINTMENT",
            "get_patient_appointment": "VIEW_OWN_APPOINTMENTS",
            "search_available_slots": "SEARCH_AVAILABLE_SLOTS",
            "create_human_escalation": "REQUEST_HUMAN_ESCALATION",
            "get_procedure": "QUERY_PREP_PROTOCOL",
            "search_prep_protocol": "QUERY_PREP_PROTOCOL"
        }

        req_perm = permission_map.get(action)
        if req_perm and not check_permission(norm_role, req_perm):
            return False, f"Unauthorized: Patient role lacks permission '{req_perm}' for action '{action}'."
        
        # Staff/admin only actions
        staff_only_actions = ["VIEW_AUDIT_LOGS", "VIEW_ALL_PATIENTS", "RESET_EHR", "OVERRIDE_CLINICAL_RESTRICTION"]
        if action in staff_only_actions:
            return False, f"Unauthorized: Action '{action}' requires STAFF or ADMIN privileges."

    return True, "Authorized"
