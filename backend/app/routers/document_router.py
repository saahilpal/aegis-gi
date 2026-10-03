import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select

from ..db.database import get_db_session
from ..db.models import DocumentChunk as DocumentChunkModel
from ..agent.llm import llm_client

router = APIRouter(prefix="/api/documents", tags=["Document Ingestion & Knowledge Base"])

class IngestTextRequest(BaseModel):
    title: str
    source_file: str = "clinical_guideline.md"
    section: str = "General"
    content: str

@router.get("")
async def list_documents():
    """List all indexed clinical guidelines and document chunks in the database."""
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
async def ingest_text(req: IngestTextRequest):
    """Ingest a clinical guideline section, embed via Gemini, and store in database."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")

    # Generate 768-dim vector embedding
    embedding_vec = llm_client.embed_text(f"{req.title} {req.section} {req.content}")

    chunk_id = str(uuid.uuid4())
    async with get_db_session() as session:
        chunk = DocumentChunkModel(
            id=chunk_id,
            title=req.title,
            source_file=req.source_file,
            section=req.section,
            content=req.content,
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
    file: UploadFile = File(...),
    title: str = Form(...),
    section: Optional[str] = Form("General Clinical Protocol")
):
    """Upload and ingest a clinical document file (txt, md, pdf text)."""
    content_bytes = await file.read()
    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback decode with ignore
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
            chunk_section = f"{section} (Part {idx + 1})" if len(paragraphs) > 1 else section
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
