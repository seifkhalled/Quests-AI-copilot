import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.core.config import settings
from src.db.supabase import supabase_client
from src.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)

# Singletons — initialised once at import time
_qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
_embedding_service = get_embedding_service()


# ── TOOL 1: Semantic Search ────────────────────────────────────────

async def semantic_search(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict]:
    """
    Embeds the query with the same sentence-transformers model used
    during ingestion, then searches Qdrant for the most relevant chunks.
    Optionally scopes results to a single document via document_id filter.

    Returns list of:
      { content, document_title, chunk_index, score, document_id }
    """
    logger.debug(f"semantic_search called with query length={len(query)}")

    # Step 1 — embed the query using the same model as the ingestion pipeline
    query_vector = _embedding_service.embed_text(query)

    # Step 2 — build optional filter
    search_filter = None
    if document_id:
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    # Step 3 — search Qdrant
    results = _qdrant_client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=top_k,
        query_filter=search_filter,
        with_payload=True,
    )

    # Step 4 — normalise output
    chunks = []
    for r in results:
        chunks.append(
            {
                "content": r.payload.get("content", ""),
                "document_title": r.payload.get("document_title", ""),
                "chunk_index": r.payload.get("chunk_index", 0),
                "score": float(r.score),
                "document_id": r.payload.get("document_id", ""),
            }
        )

    logger.info(f"Semantic search returned {len(chunks)} chunks")
    return chunks


# ── TOOL 2: Preference Extractor ──────────────────────────────────

async def extract_and_save_preferences(
    user_id: str,
    extracted: dict,
) -> None:
    """
    Merges newly extracted preferences into the candidate_profiles table.
    Only updates fields that have non-empty values.
    Uses union logic for list fields to avoid overwriting existing data.
    """
    if not extracted:
        return

    try:
        # Fetch existing profile using asyncpg supabase_client
        row = await supabase_client.fetchrow(
            "SELECT * FROM candidate_profiles WHERE user_id = $1",
            user_id,
        )

        if not row:
            logger.warning(f"No candidate profile found for user {user_id}. Creating one on the fly.")
            await supabase_client.execute(
                "INSERT INTO candidate_profiles (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
                user_id
            )
            row = await supabase_client.fetchrow(
                "SELECT * FROM candidate_profiles WHERE user_id = $1",
                user_id,
            )
            if not row:
                logger.error(f"Failed to create candidate profile for user {user_id}")
                return

        existing = dict(row)
        set_clauses = []
        values = []
        idx = 1

        # Merge tech_stack — union, deduplicated
        new_stack = extracted.get("tech_stack", [])
        if new_stack:
            merged = list(set(existing.get("tech_stack") or []) | set(new_stack))
            set_clauses.append(f"tech_stack = ${idx}")
            values.append(merged)
            idx += 1

        # Merge preferred_roles — union, deduplicated
        new_roles = extracted.get("preferred_roles", [])
        if new_roles:
            merged_roles = list(
                set(existing.get("preferred_roles") or []) | set(new_roles)
            )
            set_clauses.append(f"preferred_roles = ${idx}")
            values.append(merged_roles)
            idx += 1

        # Only set experience_years if not already stored
        new_years = extracted.get("experience_years")
        if new_years is not None and existing.get("experience_years") is None:
            set_clauses.append(f"experience_years = ${idx}")
            values.append(new_years)
            idx += 1

        # Update summary if provided
        new_summary = extracted.get("summary")
        if new_summary:
            set_clauses.append(f"summary = ${idx}")
            values.append(new_summary)
            idx += 1

        if set_clauses:
            values.append(user_id)
            query = (
                f"UPDATE candidate_profiles SET {', '.join(set_clauses)} "
                f"WHERE user_id = ${idx}"
            )
            await supabase_client.execute(query, *values)
            logger.info(f"Updated profile for user [REDACTED]: fields={set_clauses}")

    except Exception as e:
        logger.error(f"extract_and_save_preferences failed: {e}")


# ── TOOL 3: Build Context String ──────────────────────────────────

def build_context_string(chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into a readable context block for LLM prompts.
    Sorts by document_title then chunk_index to preserve narrative order.
    """
    if not chunks:
        return "No relevant context found in the knowledge base."

    sorted_chunks = sorted(
        chunks, key=lambda c: (c["document_title"], c["chunk_index"])
    )
    lines = []
    for c in sorted_chunks:
        lines.append(
            f"--- Source: {c['document_title']} "
            f"(chunk {c['chunk_index']}, score: {c['score']:.2f}) ---\n"
            f"{c['content']}"
        )
    return "\n\n".join(lines)


# ── TOOL 4: Format History for Prompt ─────────────────────────────

def format_history_for_prompt(history: list) -> str:
    """
    Converts LangChain BaseMessage list to a readable string for prompts.
    Truncates each message at 300 chars to stay within token budget.
    """
    if not history:
        return "No previous conversation."

    lines = []
    for msg in history:
        role = "User" if msg.type == "human" else "Assistant"
        lines.append(f"{role}: {msg.content[:300]}")
    return "\n".join(lines)
