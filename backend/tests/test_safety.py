from backend.app.agent.safety import evaluate_safety

def test_safety_detects_severe_bleeding():
    res = evaluate_safety("I am having severe bleeding and passing large blood clots into the toilet!")
    assert not res.is_safe
    assert res.requires_escalation is True
    assert res.urgency_level == "EMERGENCY_911"
    assert "hemorrhage" in res.escalation_reason.lower()

def test_safety_detects_severe_abdominal_pain():
    res = evaluate_safety("I have unbearable severe abdominal pain 10/10 in my belly.")
    assert not res.is_safe
    assert res.requires_escalation is True
    assert res.urgency_level == "EMERGENCY_911"

def test_safety_detects_respiratory_distress():
    res = evaluate_safety("I can't breathe and my throat is closing after the prep!")
    assert not res.is_safe
    assert res.requires_escalation is True
    assert res.urgency_level == "EMERGENCY_911"

def test_safety_detects_syncope():
    res = evaluate_safety("I just passed out and fainted on the bathroom floor.")
    assert not res.is_safe
    assert res.requires_escalation is True
    assert res.urgency_level == "EMERGENCY_911"

def test_safety_passes_normal_prep_question():
    res = evaluate_safety("Can I drink yellow Gatorade with my MiraLAX prep?")
    assert res.is_safe is True
    assert res.requires_escalation is False
    assert res.urgency_level == "NONE"
