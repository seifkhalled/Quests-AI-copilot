from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from src.db import supabase

router = APIRouter()


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    title: str
    source_type: str
    status: str
    created_at: datetime | None = None
    chunk_count: int = 0
    file_url: str | None = None


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
):
    try:
        if status:
            query = """
                SELECT d.id, d.title, d.source_type, d.status, d.created_at,
                       (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) as chunk_count
                FROM documents d
                WHERE d.status = $1
                ORDER BY d.created_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await supabase.supabase_client.fetch(query, status, limit, skip)
        else:
            query = """
                SELECT d.id, d.title, d.source_type, d.status, d.created_at,
                       (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) as chunk_count
                FROM documents d
                ORDER BY d.created_at DESC
                LIMIT $1 OFFSET $2
            """
            rows = await supabase.supabase_client.fetch(query, limit, skip)
        
        docs = []
        for row in rows:
            docs.append({
                "id": str(row["id"]),
                "title": row["title"],
                "source_type": row["source_type"],
                "status": row["status"],
                "created_at": str(row["created_at"]) if row["created_at"] else None,
                "chunk_count": row.get("chunk_count", 0) or 0,
                "file_url": None,
            })
        return docs
    except Exception as e:
        print(f"Error in list_documents: {e}")
        raise


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    query = """
        SELECT id, title, source_type, status, created_at
        FROM documents WHERE id = $1
    """
    row = await supabase.supabase_client.fetchrow(query, doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(row["id"]),
        "title": row["title"],
        "source_type": row["source_type"],
        "status": row["status"],
        "created_at": str(row["created_at"]) if row["created_at"] else None,
    }


@router.get("/{doc_id}/chunks")
async def get_document_chunks(doc_id: str):
    query = """
        SELECT id, chunk_index, content, token_count, created_at
        FROM chunks 
        WHERE document_id = $1
        ORDER BY chunk_index
    """
    rows = await supabase.supabase_client.fetch(query, doc_id)
    return [dict(row) for row in rows] if rows else []


@router.get("/{doc_id}/content")
async def get_document_content(doc_id: str):
    query = """
        SELECT raw_text 
        FROM documents 
        WHERE id = $1
    """
    row = await supabase.supabase_client.fetchrow(query, doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="Document content not found")
    return {"content": row.get("raw_text", "")}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    query = "DELETE FROM documents WHERE id = $1 RETURNING id"
    row = await supabase.supabase_client.fetchrow(query, doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": str(row["id"])}