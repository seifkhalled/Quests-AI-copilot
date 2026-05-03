import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from src.agent.graph import agent_graph
from src.services.message_service import (
    save_user_message,
    mark_conversation_ended,
    get_all_messages,
    get_context_window,
    save_assistant_message,
)
from src.services.vector import get_vector_service
from src.services.embedding import get_embedding_service
from src.agent.tools import build_context_string, extract_and_save_preferences
from src.agent.prompts import QUEST_SEARCH_PROMPT, STREAMING_CHAT_PROMPT, PREFERENCE_EXTRACTION_PROMPT
from src.agent.nodes import _llm_structured, _parse_json
from src.agent.guards import check_safety
from src.core.config import settings
from langchain_groq import ChatGroq
from src.db.supabase_client import get_supabase

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class ChatRequest(BaseModel):
    conversation_id: str
    user_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float | None
    intent: str | None
    conversation_id: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint. One turn = one call to this endpoint.

    Order of operations:
    1. Validate input and conversation ownership
    2. Check conversation is not ended
    3. Save user message to Supabase BEFORE agent runs
    4. Run LangGraph agent (load_context reads from Supabase)
    5. Agent write_memory node saves assistant message to Supabase
    6. Return response

    Message persistence guarantee:
    - User message is saved before agent runs
    - If agent crashes, user message is still in DB
    - Assistant message saved inside agent after final_response is ready
    """

    # ── Validate input ──────────────────────────────────────────
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if len(request.message) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Message too long — maximum 2000 characters"
        )

    # ── Validate conversation ───────────────────────────────────
    sb = get_supabase()
    conv_result = sb.table("conversations") \
        .select("id, user_id, scope, scoped_document_id, status") \
        .eq("id", request.conversation_id) \
        .single() \
        .execute()

    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv = conv_result.data

    if conv["user_id"] != request.user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized for this conversation"
        )

    if conv.get("status") == "ended":
        raise HTTPException(
            status_code=400,
            detail="This conversation has ended. Start a new one."
        )

    # ── Save user message immediately ───────────────────────────
    # Saved BEFORE agent runs so it is never lost
    save_user_message(
        conversation_id=request.conversation_id,
        content=request.message.strip()
    )

    # ── Build initial agent state ───────────────────────────────
    initial_state = {
        "conversation_id": request.conversation_id,
        "user_id": request.user_id,
        "user_message": request.message.strip(),
        "history": [],               # filled by load_context node
        "intent": None,
        "injection_detected": False,
        "retrieved_chunks": [],
        "extracted_preferences": None,
        "insight": None,
        "draft_response": None,
        "sources": [],
        "confidence": None,
        "reasoning": None,
        "safety_passed": False,
        "rewrite_instruction": None,
        "safety_retries": 0,
        "final_response": None,
    }

    # ── Run LangGraph agent ─────────────────────────────────────
    # write_memory node inside the graph saves the assistant message
    try:
        final_state = await agent_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(
            f"Agent failed for conversation {request.conversation_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Agent encountered an error. Please try again."
        )

    return ChatResponse(
        answer=final_state.get("final_response") or "I could not generate a response.",
        sources=final_state.get("sources", []),
        confidence=final_state.get("confidence"),
        intent=final_state.get("intent"),
        conversation_id=request.conversation_id,
    )


class StreamChatRequest(BaseModel):
    conversation_id: str
    user_id: str
    message: str


async def stream_generate(
    conversation_id: str,
    user_id: str,
    message: str,
):
    """Streaming LLM generation with SSE."""
    embedding_service = get_embedding_service()
    vector_service = get_vector_service()
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        api_key=settings.GROQ_AGENT_API_KEY,
    )

    yield {"type": "start", "conversation_id": conversation_id}

    try:
        raw_messages = get_context_window(conversation_id)
        history = []
        for m in raw_messages:
            if m["role"] == "user":
                history.append({"role": "user", "content": m["content"]})
            else:
                history.append({"role": "assistant", "content": m["content"]})

        yield {"type": "status", "content": "Searching knowledge base..."}
        query_embedding = embedding_service.embed_text(message)
        results = await vector_service.search(
            query_vector=query_embedding,
            limit=5,
        )

        if not results:
            yield {"type": "content", "content": "I don't have any relevant information to answer your question."}
            return

        formatted_chunks = [
            {
                "content": r.get("content", ""),
                "document_title": r.get("metadata", {}).get("document_title", "Unknown Document"),
                "chunk_index": r.get("metadata", {}).get("chunk_index", 0),
                "score": r.get("score", 0.0),
            }
            for r in results
        ]
        context = build_context_string(formatted_chunks)
        history_str = "\n".join(
            f"{h['role'].capitalize()}: {h['content']}" for h in history
        ) or "No previous messages"

        prompt = STREAMING_CHAT_PROMPT.format(
            context=context,
            candidate_profile="No profile data yet",
            history=history_str,
            user_message=message,
        )

        yield {"type": "status", "content": "Generating response..."}

        full_content = ""
        async for chunk in llm.astream(prompt):
            content = chunk.content
            if content:
                full_content += content
                yield {"type": "content", "content": content}

        formatted_sources = [
            {
                "document_title": r.get("metadata", {}).get("document_title", "Unknown Document"),
                "chunk_index": r.get("metadata", {}).get("chunk_index", 0),
                "snippet": r.get("content", ""),
                "score": r.get("score", 0.0),
            }
            for r in results
        ]

        save_user_message(conversation_id=conversation_id, content=message)
        save_assistant_message(
            conversation_id=conversation_id,
            content=full_content,
            sources=formatted_sources,
            confidence=sum(r["score"] for r in results) / len(results) * 2 if results else 0.0,
        )

        yield {"type": "sources", "sources": formatted_sources}

        # ── Background Preference Extraction ──────────────────────
        # This keeps the profile updated as the user shares info
        async def run_extraction():
            try:
                extract_prompt = PREFERENCE_EXTRACTION_PROMPT.format(user_message=message)
                res = await _llm_structured.ainvoke(extract_prompt)
                extracted_data = _parse_json(res.content)
                if extracted_data:
                    await extract_and_save_preferences(user_id, extracted_data)
            except Exception as e:
                logger.error(f"Background preference extraction failed: {e}")

        asyncio.create_task(run_extraction())

    except Exception as e:
        logger.error(f"Stream chat failed: {e}")
        yield {"type": "error", "error": str(e)}


@router.post("/stream")
async def stream_chat(request: StreamChatRequest):
    """Streaming chat endpoint using SSE."""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    sb = get_supabase()
    conv_result = sb.table("conversations") \
        .select("id, user_id, status") \
        .eq("id", request.conversation_id) \
        .single() \
        .execute()

    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv = conv_result.data
    if conv["user_id"] != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if conv.get("status") == "ended":
        raise HTTPException(status_code=400, detail="Conversation ended")

    async def event_generator():
        try:
            async for event in stream_generate(
                request.conversation_id,
                request.user_id,
                request.message,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/{conversation_id}/end")
async def end_conversation(conversation_id: str, user_id: str):
    """
    Ends a conversation.

    Since messages are written to Supabase in real time on every turn,
    there is nothing to flush here. Every message is already persisted.

    This endpoint simply:
    1. Validates the user owns the conversation
    2. Sets status = 'ended' and last_message_at = now in Supabase
    3. Returns confirmation

    After this call, POST /api/chat will return 400 for this conversation.
    """
    sb = get_supabase()

    conv = sb.table("conversations") \
        .select("user_id, status") \
        .eq("id", conversation_id) \
        .single() \
        .execute()

    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if conv.data.get("status") == "ended":
        return {
            "status": "already ended",
            "conversation_id": conversation_id
        }

    result = mark_conversation_ended(conversation_id)

    return {
        "status": "conversation ended",
        "conversation_id": conversation_id,
        "last_message_at": result.get("last_message_at"),
    }


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str, user_id: str):
    """
    Returns ALL messages for a conversation in chronological order.
    Used by the frontend to render the full chat history.

    Note: the agent uses only the last 10 messages (5 turns) as
    its sliding context window. This endpoint returns everything
    regardless of window size — it is for display only.
    """
    sb = get_supabase()

    conv = sb.table("conversations") \
        .select("user_id") \
        .eq("id", conversation_id) \
        .single() \
        .execute()

    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    messages = get_all_messages(conversation_id)

    return {
        "conversation_id": conversation_id,
        "message_count": len(messages),
        "messages": messages,
    }
