import json
import logging
from datetime import datetime, timezone
from src.db.supabase_client import get_supabase
from src.core.config import settings

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def save_insight(
    title: str,
    body: str,
    category: str,
    source_document_ids: list,
    relevance_score: float,
) -> dict | None:
    """
    Saves a single insight row to the insights table.
    category must be one of: pattern | conflict | decision | issue
    """
    sb = get_supabase()
    try:
        result = sb.table("insights").insert({
            "title": title,
            "body": body,
            "category": category,
            "source_document_ids": source_document_ids,
            "relevance_score": relevance_score,
            "generated_at": now_iso(),
        }).execute()
        logger.info(f"Saved insight: {title[:60]}")
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Failed to save insight: {e}")
        return None


async def save_conversation_insight(
    insight_text: str,
    sources: list,
    confidence: float,
) -> None:
    """
    Called from write_memory node when intent = insight_request
    and confidence >= 0.7. Saves the agent-generated insight
    so it can be surfaced in GET /api/ai/insights without
    re-generating.

    source_document_ids is derived from the sources list
    using document_title as identifier.
    """
    if confidence < 0.7:
        logger.debug("Insight confidence too low — skipping save")
        return

    source_titles = list({
        s.get("document_title", "") for s in sources
        if s.get("document_title")
    })

    await save_insight(
        title=insight_text[:80],
        body=insight_text,
        category="pattern",
        source_document_ids=source_titles,
        relevance_score=confidence,
    )


async def generate_post_ingestion_insights(document_id: str) -> None:
    """
    Called as a BackgroundTask after a document reaches
    status = 'processed' in the ingestion pipeline.

    Reads the document's chunks from Supabase, sends them
    to the LLM, and saves 1-3 document-level insights.

    These insights describe the quest itself:
    required skills, experience level, salary signals,
    location, anything notable.
    """
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    sb = get_supabase()

    # Fetch document
    doc_result = sb.table("documents") \
        .select("title, source_type") \
        .eq("id", document_id) \
        .single().execute()

    if not doc_result.data:
        logger.warning(f"Document {document_id} not found for insight generation")
        return

    doc_title = doc_result.data["title"]

    # Fetch all chunks for this document ordered by chunk_index
    chunks_result = sb.table("chunks") \
        .select("content, chunk_index") \
        .eq("document_id", document_id) \
        .order("chunk_index", desc=False) \
        .execute()

    if not chunks_result.data:
        logger.warning(f"No chunks found for document {document_id}")
        return

    # Build context from chunks (cap at 3000 chars to avoid large prompts)
    context = "\n\n".join(
        c["content"] for c in chunks_result.data
    )[:3000]

    prompt = f"""
Analyze this job quest document and extract 1 to 3 key insights.
Focus on: required skills, experience level, salary signals,
location, and anything that stands out for a job seeker.
Never produce code of any kind.

Document: {doc_title}

Content:
{context}

Return a JSON array of insight objects with exactly these keys:
[
  {{
    "title": "short title under 80 chars",
    "body": "full insight as one or two sentences",
    "category": "one of: pattern | conflict | decision | issue"
  }}
]

Return only valid JSON. No markdown, no preamble.
"""

    try:
        result = llm.invoke(prompt)
        raw = result.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        insights = json.loads(raw.strip())

        for insight in insights:
            await save_insight(
                title=insight.get("title", doc_title[:80]),
                body=insight.get("body", ""),
                category=insight.get("category", "pattern"),
                source_document_ids=[document_id],
                relevance_score=0.8,
            )

        logger.info(
            f"Generated {len(insights)} post-ingestion insights "
            f"for document {document_id} ({doc_title})"
        )

    except Exception as e:
        logger.error(
            f"Post-ingestion insight generation failed "
            f"for document {document_id}: {e}"
        )
