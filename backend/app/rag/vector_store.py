import math
import re
from typing import List, Dict, Any, Tuple
from sqlalchemy import select

from ..db.database import get_db_session, is_sqlite
from ..db.models import DocumentChunk as DocumentChunkModel
from ..agent.llm import llm_client
from ..ehr.ehr_service import run_async

STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
    "is", "was", "are", "were", "of", "can", "i", "my", "while", "do",
    "you", "your", "it", "this", "that", "be", "have", "has", "had", "as",
    "by", "if", "not", "but", "what", "which", "how", "when", "where", "who"
}

class VectorStore:
    """
    Production Vector Store querying PostgreSQL pgvector (or async SQLite).
    Computes real cosine distance on 768-dimensional embeddings generated via Gemini / text embeddings.
    """

    async def search_async(self, query: str, top_k: int = 2) -> List[Tuple[Dict[str, Any], float]]:
        if not query or not query.strip():
            return []

        # Generate query vector
        query_vec = llm_client.embed_text(query)

        async with get_db_session() as session:
            # Query all active document chunks
            stmt = select(DocumentChunkModel)
            chunks = (await session.execute(stmt)).scalars().all()

            if not chunks:
                return []

            scored: List[Tuple[Dict[str, Any], float]] = []

            def cosine_similarity(v1: List[float], v2: List[float]) -> float:
                if not v1 or not v2 or len(v1) != len(v2):
                    return 0.0
                norm1 = math.sqrt(sum(a * a for a in v1))
                norm2 = math.sqrt(sum(b * b for b in v2))
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                dot = sum(a * b for a, b in zip(v1, v2))
                return max(0.0, min(1.0, dot / (norm1 * norm2)))

            # Meaningful clinical query keywords (non-stopwords)
            raw_tokens = re.findall(r'\b[a-zA-Z0-9_\-\./]+\b', query.lower())
            meaningful_terms = [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 2]

            for c in chunks:
                emb = c.embedding
                cos_sim = 0.0
                if emb and isinstance(emb, list) and len(emb) == 768:
                    cos_sim = cosine_similarity(query_vec, emb)
                
                # Check lexical term match in chunk content
                c_content_lower = c.content.lower()
                c_section_lower = c.section.lower()
                c_title_lower = c.title.lower()
                
                matched_terms = [
                    t for t in meaningful_terms
                    if t in c_content_lower or t in c_section_lower or t in c_title_lower
                ]
                
                if meaningful_terms:
                    overlap_ratio = len(matched_terms) / len(meaningful_terms)
                else:
                    overlap_ratio = 0.0

                # If no meaningful terms match and cosine similarity is low, this document is irrelevant
                if not matched_terms and cos_sim < 0.20:
                    score = 0.0
                else:
                    # Hybrid score: embedding similarity + term frequency weighting
                    lexical_score = min(0.60, overlap_ratio * 0.6)
                    score = round(min(1.0, cos_sim * 0.5 + lexical_score), 3)

                doc_dict = {
                    "document_name": c.source_file,
                    "section": c.section,
                    "content": c.content,
                    "title": c.title,
                }
                scored.append((doc_dict, score))

            # Sort descending
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

    def search(self, query: str, top_k: int = 2) -> List[Tuple[Dict[str, Any], float]]:
        return run_async(self.search_async(query, top_k=top_k))

vector_store = VectorStore()
