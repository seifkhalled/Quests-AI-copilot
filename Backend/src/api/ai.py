from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from pydantic import BaseModel
from src.db.supabase_client import get_supabase

router = APIRouter()

class InsightResponse(BaseModel):
    id: str
    title: str
    body: str
    category: str
    source_document_ids: List[str]
    relevance_score: float
    generated_at: str

@router.get("/insights", response_model=List[InsightResponse])
async def get_insights(limit: int = 20):
    """
    Returns the latest insights generated across all documents.
    Used by the frontend to show the 'Latest Insights' section.
    """
    sb = get_supabase()
    try:
        result = sb.table("insights") \
            .select("*") \
            .order("generated_at", desc=True) \
            .limit(limit) \
            .execute()
        
        if not result.data:
            return []
            
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
