import logging
from datetime import datetime, timezone
from src.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

CONTEXT_WINDOW_TURNS = 5  # last 5 turns = last 10 messages


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_user_message(conversation_id: str, content: str) -> dict:
    """
    Saves the user message to Supabase immediately.
    Called BEFORE the agent runs so the message is never lost
    even if the agent crashes.
    """
    sb = get_supabase()
    result = sb.table("messages").insert({
        "conversation_id": conversation_id,
        "role": "user",
        "content": content,
        "created_at": now_iso(),
    }).execute()
    logger.debug(f"Saved user message for conversation {conversation_id}")
    return result.data[0] if result.data else {}


def save_assistant_message(
    conversation_id: str,
    content: str,
    sources: list | None = None,
    confidence: float | None = None,
    reasoning: str | None = None,
) -> dict:
    """
    Saves the assistant message to Supabase after the agent responds.
    Also updates conversations.last_message_at to now.
    """
    sb = get_supabase()

    result = sb.table("messages").insert({
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": content,
        "sources": sources or [],
        "confidence": confidence,
        "reasoning": reasoning,
        "created_at": now_iso(),
    }).execute()

    sb.table("conversations").update({
        "last_message_at": now_iso()
    }).eq("id", conversation_id).execute()

    logger.debug(f"Saved assistant message for conversation {conversation_id}")
    return result.data[0] if result.data else {}


def get_context_window(conversation_id: str) -> list[dict]:
    """
    Sliding window — returns the last CONTEXT_WINDOW_TURNS * 2
    messages (last 10 rows) in chronological order (oldest first).

    Behavior:
      Turn 1:  [m1]
      Turn 2:  [m1, m2]
      Turn 5:  [m1, m2, m3, m4, m5]
      Turn 6:  [m2, m3, m4, m5, m6]   ← m1 slides out
      Turn 7:  [m3, m4, m5, m6, m7]   ← m2 slides out

    Always the most recent 10 messages regardless of total count.
    Returns empty list if no messages exist yet (new conversation).
    """
    sb = get_supabase()
    limit = CONTEXT_WINDOW_TURNS * 2  # 10 messages = 5 full turns

    try:
        result = sb.table("messages") \
            .select("role, content, created_at") \
            .eq("conversation_id", conversation_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        # Reverse to restore chronological order oldest → newest
        messages = list(reversed(result.data or []))
        logger.debug(
            f"Loaded {len(messages)} messages from Supabase "
            f"for conversation {conversation_id}"
        )
        return messages

    except Exception as e:
        logger.error(f"Failed to load context window: {e}")
        return []


def get_all_messages(conversation_id: str) -> list[dict]:
    """
    Returns ALL messages for a conversation in chronological order.
    Used only by the frontend to render full chat history.
    Never used by the agent — agent uses get_context_window only.
    """
    sb = get_supabase()
    try:
        result = sb.table("messages") \
            .select("*") \
            .eq("conversation_id", conversation_id) \
            .order("created_at", desc=False) \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to load all messages: {e}")
        return []


def mark_conversation_ended(conversation_id: str) -> dict:
    """
    Marks a conversation as ended in Supabase.
    Since all messages are written in real time, there is nothing
    to flush — every message is already in the database.
    Simply updates status = 'ended' and last_message_at = now.
    """
    sb = get_supabase()
    try:
        result = sb.table("conversations").update({
            "status": "ended",
            "last_message_at": now_iso(),
        }).eq("id", conversation_id).execute()
        logger.info(f"Conversation {conversation_id} marked as ended")
        return result.data[0] if result.data else {}
    except Exception as e:
        logger.error(f"Failed to end conversation {conversation_id}: {e}")
        return {}
