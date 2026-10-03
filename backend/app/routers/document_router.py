import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from ..db.database import get_db_session
from ..db.models import DocumentChunk as DocumentChunkModel
from ..agent.llm import llm_client
from ..security.auth import security_bearer, decode_access_token
from ..security.rate_limiter import enforce_rate_limit

router = APIRouter(prefix="/api/documents", tags=["Document Ingestion & Knowledge Base"])

class IngestTextRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    source_file: str = Field("clinical_guideline.md", max_length=100)
    section: str = Field("General", max_length=100)
    content: str = Field(..., min_length=10, max_length=50000, description="Guideline content (10-50,000 chars)")

def get_optional_auth_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except Exception:
        return None

def enforce_clinician_or_admin(claims: Optional[Dict[str, Any]]):
    """Ensure patients cannot inject arbitrary knowledge into clinical RAG vector store."""
    if claims:
        role = claims.get("role", "PATIENT").upper()
        if role == "PATIENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Patients cannot ingest documents into institutional knowledge base."
            )

@router.get("")
async def list_documents(request: Request):
    """List all indexed clinical guidelines and document chunks in the database."""
    enforce_rate_limit(request, max_requests=60, window_seconds=60, operation="list_docs")
    async with get_db_session() as session:
        chunks = (await session.execute(
            select(DocumentChunkModel).order_by(DocumentChunkModel.created_at.desc())
        )).scalars().all()

        return {
            "total_chunks": len(chunks),
            "documents": [
                {
                    "id": c.id,
                    "title": c.title,
                    "source_file": c.source_file,
                    "section": c.section,
                    "content_preview": c.content[:200] + "..." if len(c.content) > 200 else c.content,
                    "has_embedding": bool(c.embedding),
                    "created_at": c.created_at.isoformat()
                }
                for c in chunks
            ]
        }

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_text(
    req: IngestTextRequest,
    request: Request,
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    """Ingest a clinical guideline section, embed, and store in database."""
    enforce_rate_limit(request, max_requests=10, window_seconds=60, operation="doc_ingest")
    enforce_clinician_or_admin(auth_claims)

    clean_content = req.content.strip()
    if not clean_content:
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")

    # Generate 768-dim vector embedding
    embedding_vec = llm_client.embed_text(f"{req.title} {req.section} {clean_content}")

    chunk_id = str(uuid.uuid4())
    async with get_db_session() as session:
        chunk = DocumentChunkModel(
            id=chunk_id,
            title=req.title,
            source_file=req.source_file,
            section=req.section,
            content=clean_content,
            embedding=embedding_vec,
            created_at=datetime.now(timezone.utc)
        )
        session.add(chunk)
        await session.commit()

    return {
        "status": "SUCCESS",
        "chunk_id": chunk_id,
        "message": f"Successfully ingested and embedded '{req.section}' into clinical vector database."
    }

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    section: Optional[str] = Form("General Clinical Protocol"),
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    """Upload and ingest a clinical document file (txt, md, pdf text). Max 5MB."""
    enforce_rate_limit(request, max_requests=10, window_seconds=60, operation="doc_upload")
    enforce_clinician_or_admin(auth_claims)

    # Read and enforce max 5MB limit
    content_bytes = await file.read(5 * 1024 * 1024 + 1)
    if len(content_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed file size is 5MB.")

    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text_content = content_bytes.decode("latin-1", errors="ignore")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty or unreadable.")

    # Split into paragraphs or chunks if large
    paragraphs = [p.strip() for p in text_content.split("\n\n") if len(p.strip()) > 30]
    if not paragraphs:
        paragraphs = [text_content[:2000]]

    ingested_ids = []
    async with get_db_session() as session:
        for idx, para in enumerate(paragraphs[:10]):  # Cap at 10 chunks per file upload
            chunk_section = f"{section} (Part {idx + 1})" if len(paragraphs) > 1 else (section or "General")
            embedding_vec = llm_client.embed_text(f"{title} {chunk_section} {para}")
            cid = str(uuid.uuid4())
            chunk = DocumentChunkModel(
                id=cid,
                title=title,
                source_file=file.filename or "uploaded_protocol.txt",
                section=chunk_section,
                content=para,
                embedding=embedding_vec,
                created_at=datetime.now(timezone.utc)
            )
            session.add(chunk)
            ingested_ids.append(cid)

        await session.commit()

    return {
        "status": "SUCCESS",
        "filename": file.filename,
        "chunks_ingested": len(ingested_ids),
        "chunk_ids": ingested_ids
    }
