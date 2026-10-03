import re
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel

class SafetyCheckResult(BaseModel):
    is_safe: bool
    requires_escalation: bool
    urgency_level: str  # "EMERGENCY_911", "ON_CALL_PHYSICIAN", "CLINIC_STAFF", "NONE"
    escalation_reason: Optional[str] = None
    matched_symptom: Optional[str] = None
    patient_guidance: Optional[str] = None

# Red-flag clinical patterns during GI prep
RED_FLAG_PATTERNS = [
    {
        "category": "SEVERE_BLEEDING",
        "regex": r"\b(severe bleeding|heavy bleeding|bleeding heavily|passing (large )?clots|bright red blood filling|toilet bowl full of blood|hemorrhag\w*)\b",
        "urgency": "EMERGENCY_911",
        "reason": "Suspected massive lower gastrointestinal hemorrhage or hemodynamic compromise",
        "guidance": "Please stop taking your bowel prep immediately and call 911 or proceed to the nearest Emergency Department. Large-volume rectal bleeding is a medical emergency requiring in-person evaluation."
    },
    {
        "category": "SEVERE_ABDOMINAL_PAIN",
        "regex": r"\b(severe (abdominal|stomach|belly) pain|unbearable pain|excruciating pain|10/10 pain|agony in my stomach|rigid abdomen)\b",
        "urgency": "EMERGENCY_911",
        "reason": "Severe acute abdomen / suspected bowel perforation or acute obstruction",
        "guidance": "Severe, intractable abdominal pain is not expected during routine bowel preparation. Please stop taking the preparation solution and call 911 or go to the nearest emergency room immediately."
    },
    {
        "category": "RESPIRATORY_DISTRESS",
        "regex": r"\b(difficulty breathing|can't breathe|cannot breathe|shortness of breath|stridor|wheezing severely|throat (is )?closing|anaphylaxis|swollen lips and tongue)\b",
        "urgency": "EMERGENCY_911",
        "reason": "Suspected acute anaphylaxis or severe airway compromise",
        "guidance": "Immediate medical attention is required. Please call 911 immediately. If you have an epinephrine auto-injector (EpiPen) for severe allergies, use it as prescribed."
    },
    {
        "category": "LOSS_OF_CONSCIOUSNESS",
        "regex": r"\b(passed out|fainted|loss of consciousness|blacked out|collapsed|syncope|unresponsive)\b",
        "urgency": "EMERGENCY_911",
        "reason": "Vasovagal syncope or acute volume depletion with loss of consciousness",
        "guidance": "Loss of consciousness during bowel preparation indicates acute dehydration or vasovagal syncope. Please call 911 immediately and lie flat with legs elevated until medical responders arrive."
    },
    {
        "category": "INTRACTABLE_VOMITING",
        "regex": r"\b(can't keep anything down|throwing up continuously|vomiting everything|inability to retain fluids|vomited more than 5 times)\b",
        "urgency": "ON_CALL_PHYSICIAN",
        "reason": "Persistent intractable emesis preventing prep completion and risking electrolyte derangement",
        "guidance": "Persistent vomiting prevents safe completion of your procedure prep. I am escalating your chart to our On-Call GI Triage Nurse immediately. Please rest and take small sips of water while our clinical staff contacts you."
    },
    {
        "category": "OUT_OF_SCOPE_DIAGNOSIS",
        "regex": r"\b(diagnose (this|my)|what (disease|illness) do i have|is this cancer|look at this rash|do i have a tumor|stage \d|colon cancer|biopsy)\b",
        "urgency": "CLINIC_STAFF",
        "reason": "Explicit medical diagnosis requested. AI agent strictly operates in non-diagnostic administrative/prep capacity.",
        "guidance": "As an administrative and prep guidance agent, I am not authorized to provide medical diagnoses or interpret non-prep clinical conditions. I have notified our clinic staff to connect with you regarding this inquiry."
    }
]

def evaluate_safety(user_message: str) -> SafetyCheckResult:
    """
    Evaluate user message for clinical red flags and non-diagnostic policy violations.
    Deterministic, high-reliability safety layer executing prior to LLM/tools.
    """
    clean_text = user_message.lower().strip()
    
    for rule in RED_FLAG_PATTERNS:
        match = re.search(rule["regex"], clean_text, re.IGNORECASE)
        if match:
            return SafetyCheckResult(
                is_safe=False,
                requires_escalation=True,
                urgency_level=rule["urgency"],
                escalation_reason=rule["reason"],
                matched_symptom=match.group(0),
                patient_guidance=rule["guidance"]
            )
            
    return SafetyCheckResult(
        is_safe=True,
        requires_escalation=False,
        urgency_level="NONE",
        escalation_reason=None,
        matched_symptom=None,
        patient_guidance=None
    )
