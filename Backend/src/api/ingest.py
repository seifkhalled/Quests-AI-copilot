from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional, List
import uuid
import hashlib
from pydantic import BaseModel

from src.services.ingestion import get_ingestion_service
from src.services.chunking import chunk_text
from src.services.embedding import get_embedding_service
from src.services.vector import get_vector_service
from src.db import supabase
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestResponse(BaseModel):
    document_id: str
    title: str
    chunks_created: int
    status: str


class SourceIngestRequest(BaseModel):
    source_type: str
    content: str
    title: str
    metadata: Optional[dict] = None


@router.post("/files", response_model=List[IngestResponse])
async def ingest_files(files: List[UploadFile] = File(...)):
    """Upload and process multiple files (PDF, TXT, MD)."""
    results = []
    
    for file in files:
        content = await file.read()
        if not content:
            continue
            
        filename = file.filename
        mime_type = file.content_type
        
        ingestion_service = await get_ingestion_service()
        try:
            ingested = await ingestion_service.ingest_file(content, filename, mime_type)
        except Exception as e:
            # For brevity in this pipeline fix, we skip or raise. 
            # In production, we'd collect errors.
            raise HTTPException(status_code=400, detail=f"Failed to process {filename}: {str(e)}")
            
        doc_id = str(uuid.uuid4())
        
        # Insert into documents table (schema.sql)
        await supabase.supabase_client.execute(
            """
            INSERT INTO documents (id, title, source_type, raw_text, status)
            VALUES ($1, $2, $3, $4, 'processing')
            """,
            doc_id,
            ingested.title,
            ingested.file_type.value,
            ingested.content,
        )
        
        # Chunking
        chunks = chunk_text(ingested.content, ingested.title)
        
        # Embedding
        embedding_service = get_embedding_service()
        chunk_docs = [{"content": c["content"]} for c in chunks]
        chunk_docs = embedding_service.embed_documents(chunk_docs)
        
        for i, chunk in enumerate(chunk_docs):
            chunk["chunk_index"] = chunks[i]["chunk_index"]
            chunk["token_count"] = chunks[i]["token_count"]
            chunk["document_title"] = ingested.title
            
        # Vector DB
        vector_service = get_vector_service()
        embeddings = [c["embedding"] for c in chunk_docs]
        vector_ids = await vector_service.upsert_chunks(
            document_id=doc_id,
            chunks=chunk_docs,
            embeddings=embeddings,
            metadata={"title": ingested.title}
        )
        
        # Insert into chunks table (schema.sql)
        chunk_records = [
            (
                str(uuid.uuid4()),
                doc_id,
                c["chunk_index"],
                c["content"],
                c["token_count"],
                vector_ids[i]
            )
            for i, c in enumerate(chunk_docs)
        ]
        
        await supabase.supabase_client.execute_many(
            """
            INSERT INTO chunks (id, document_id, chunk_index, content, token_count, qdrant_point_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            chunk_records,
        )
        
        # Update status
        await supabase.supabase_client.execute(
            "UPDATE documents SET status = 'processed' WHERE id = $1",
            doc_id,
        )

        # Trigger post-ingestion insight generation as background task
        try:
            from src.services.insight_service import generate_post_ingestion_insights
            import asyncio
            asyncio.create_task(generate_post_ingestion_insights(doc_id))
            logger.info(f"Scheduled post-ingestion insights for document {doc_id}")
        except Exception as e:
            # Never let insight generation failure affect pipeline status
            logger.error(f"Failed to schedule insights for {doc_id}: {e}")
        
        results.append(IngestResponse(
            document_id=doc_id,
            title=ingested.title,
            chunks_created=len(chunks),
            status="processed",
        ))
        
    return results


@router.post("/source", response_model=IngestResponse)
async def ingest_source(request: SourceIngestRequest):
    """Ingest from external source (Slack, Notion, etc)."""
    source_type = request.source_type
    content = request.content
    title = request.title
    
    if not content or not title:
        raise HTTPException(status_code=400, detail="Content and title required")
    
    # Import cleaning
    from src.services.cleaning import clean_text
    cleaned_content = clean_text(content, remove_emojis_flag=True)
    
    doc_id = str(uuid.uuid4())
    
    # Create document record
    await supabase.supabase_client.execute(
        """
        INSERT INTO documents (id, title, source_type, raw_text, status)
        VALUES ($1, $2, $3, $4, 'processing')
        """,
        doc_id,
        title,
        source_type,
        cleaned_content,
    )
    
    # Chunking
    chunks = chunk_text(cleaned_content, title)
    
    # Embedding
    embedding_service = get_embedding_service()
    chunk_docs = [{"content": c["content"]} for c in chunks]
    chunk_docs = embedding_service.embed_documents(chunk_docs)
    
    for i, chunk in enumerate(chunk_docs):
        chunk["chunk_index"] = chunks[i]["chunk_index"]
        chunk["token_count"] = chunks[i]["token_count"]
        chunk["document_title"] = title
        
    # Vector DB
    vector_service = get_vector_service()
    embeddings = [c["embedding"] for c in chunk_docs]
    vector_ids = await vector_service.upsert_chunks(
        document_id=doc_id,
        chunks=chunk_docs,
        embeddings=embeddings,
        metadata={"title": title}
    )
    
    # Save chunks to DB
    chunk_records = [
        (
            str(uuid.uuid4()),
            doc_id,
            c["chunk_index"],
            c["content"],
            c["token_count"],
            vector_ids[i]
        )
        for i, c in enumerate(chunk_docs)
    ]
    
    await supabase.supabase_client.execute_many(
        """
        INSERT INTO chunks (id, document_id, chunk_index, content, token_count, qdrant_point_id)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        chunk_records,
    )
    
    # Update status
    await supabase.supabase_client.execute(
        "UPDATE documents SET status = 'processed' WHERE id = $1",
        doc_id,
    )

    # Trigger post-ingestion insight generation as background task
    try:
        from src.services.insight_service import generate_post_ingestion_insights
        import asyncio
        asyncio.create_task(generate_post_ingestion_insights(doc_id))
        logger.info(f"Scheduled post-ingestion insights for document {doc_id}")
    except Exception as e:
        # Never let insight generation failure affect pipeline status
        logger.error(f"Failed to schedule insights for {doc_id}: {e}")
    
    return IngestResponse(
        document_id=doc_id,
        title=title,
        chunks_created=len(chunks),
        status="processed",
    )


@router.get("/health")
async def health():
    """Check ingestion service health."""
    return {"status": "healthy"}