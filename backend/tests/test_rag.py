from backend.app.rag.retriever import retrieve_prep_context

def test_rag_retrieves_split_dose_peg_protocol():
    res = retrieve_prep_context("When do I drink the split-dose MiraLAX PEG prep?")
    assert not res.is_low_confidence
    assert len(res.citations) > 0
    assert any("Split-Dose" in c.source_document or "Split-Dose" in c.source_section for c in res.citations)
    assert "2 liters" in res.content.lower()

def test_rag_retrieves_insulin_management():
    res = retrieve_prep_context("How should I adjust my Lantus insulin the night before colonoscopy?")
    assert not res.is_low_confidence
    assert len(res.citations) > 0
    assert any("Diabetic" in c.source_document for c in res.citations)
    assert "50%" in res.content

def test_rag_identifies_low_confidence_obscure_query():
    # An obscure or completely non-GI query
    res = retrieve_prep_context("Can I feed my pet parrot sunflower seeds while driving a tractor?")
    assert res.is_low_confidence is True
    assert len(res.citations) == 0
