from typing import List, Dict, Any, Optional, Tuple
from .vector_store import vector_store
from ..models.chat import Citation

CONFIDENCE_THRESHOLD = 0.50  # Minimum confidence to accept retrieval without clarification

class RetrievalResult:
    def __init__(self, content: str, citations: List[Citation], confidence: float, is_low_confidence: bool):
        self.content = content
        self.citations = citations
        self.confidence = confidence
        self.is_low_confidence = is_low_confidence

def _process_matches(matches: List[Tuple[Dict[str, Any], float]]) -> RetrievalResult:
    if not matches:
        return RetrievalResult(
            content="",
            citations=[],
            confidence=0.0,
            is_low_confidence=True
        )

    best_doc, best_score = matches[0]
    citations: List[Citation] = []
    snippets: List[str] = []

    for doc, score in matches:
        if score >= 0.20:
            citations.append(Citation(
                source_document=doc["document_name"],
                source_section=doc["section"],
                text_snippet=doc["content"][:200] + "...",
                confidence=score
            ))
            snippets.append(f"[{doc['document_name']} | {doc['section']}]\n{doc['content']}")

    is_low_confidence = best_score < CONFIDENCE_THRESHOLD
    combined_content = "\n\n".join(snippets) if not is_low_confidence else ""

    return RetrievalResult(
        content=combined_content,
        citations=citations if not is_low_confidence else [],
        confidence=best_score,
        is_low_confidence=is_low_confidence
    )

def retrieve_prep_context(query: str, top_k: int = 2) -> RetrievalResult:
    """
    Retrieve clinical context from the GI protocol knowledge base.
    Guarantees citations with source_document and source_section.
    Detects low confidence to prevent hallucinations.
    """
    matches = vector_store.search(query, top_k=top_k)
    return _process_matches(matches)

async def retrieve_prep_context_async(query: str, top_k: int = 2) -> RetrievalResult:
    """
    Async retrieval directly on running event loop for PostgreSQL asyncpg compatibility.
    """
    matches = await vector_store.search_async(query, top_k=top_k)
    return _process_matches(matches)
