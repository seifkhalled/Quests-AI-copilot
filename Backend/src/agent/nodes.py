import json
import logging
import asyncio

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.state import AgentState
from src.agent.prompts import (
    INTENT_DETECTION_PROMPT,
    QUEST_SEARCH_PROMPT,
    PREFERENCE_EXTRACTION_PROMPT,
    INSIGHT_GENERATION_PROMPT,
)
from src.agent.tools import (
    semantic_search,
    extract_and_save_preferences,
    build_context_string,
    format_history_for_prompt,
)
from src.agent.guards import check_safety
from src.core.config import settings

logger = logging.getLogger(__name__)

# LLM instances — one for structured JSON (temp=0), one for prose (temp=0.2)
_llm_structured = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=settings.GROQ_AGENT_API_KEY,
)
_llm_prose = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    api_key=settings.GROQ_AGENT_API_KEY,
)


def _parse_json(content: str) -> dict:
    """Strip markdown fences and parse JSON. Returns {} on failure."""
    try:
        clean = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception:
        return {}


# ── NODE 1: load_context ──────────────────────────────────────────

from langchain_core.messages import HumanMessage, AIMessage
from src.services.message_service import get_context_window

async def load_context(state: AgentState) -> dict:
    """
    Loads the last 5 turns (10 messages) from Supabase using a
    sliding window query.

    Sliding window behavior:
      Turn 1-5:  grows from [m1] to [m1..m10]
      Turn 6+:   slides forward — always the last 10 messages
                 oldest message drops off as new ones arrive

    Converts raw dicts to LangChain HumanMessage / AIMessage
    so the LLM can use them as conversation history.
    Returns empty history list for new conversations.
    """
    raw_messages = get_context_window(state["conversation_id"])

    history = []
    for m in raw_messages:
        if m["role"] == "user":
            history.append(HumanMessage(content=m["content"]))
        else:
            history.append(AIMessage(content=m["content"]))

    logger.info(
        f"Loaded {len(history)} messages from Supabase "
        f"for conversation {state['conversation_id']}"
    )
    return {"history": history}


# ── NODE 2: detect_intent ─────────────────────────────────────────

async def detect_intent(state: AgentState) -> dict:
    """
    Classifies user intent and checks for prompt injection.
    Forces intent to off_topic if injection is detected.
    """
    logger.debug(f"[detect_intent] conversation={state['conversation_id']}")
    history_summary = format_history_for_prompt(state["history"])

    prompt = INTENT_DETECTION_PROMPT.format(
        user_message=state["user_message"],
        history_summary=history_summary,
    )

    try:
        result = _llm_structured.invoke(prompt)
        data = _parse_json(result.content)
        intent = data.get("intent", "off_topic")
        injection = bool(data.get("injection_detected", False))

        if injection:
            logger.warning(
                f"[detect_intent] Injection attempt in conversation={state['conversation_id']}"
            )
            intent = "off_topic"

        logger.debug(f"[detect_intent] intent={intent} injection={injection}")
        return {"intent": intent, "injection_detected": injection}

    except Exception as e:
        logger.error(f"[detect_intent] failed: {e}")
        return {"intent": "off_topic", "injection_detected": False}


# ── NODE 3: route — used as conditional edge function ─────────────

def route(state: AgentState) -> str:
    """
    Maps detected intent to the next node name.
    Used as the path function in add_conditional_edges.
    """
    intent = state.get("intent", "off_topic")
    mapping = {
        "quest_search":       "run_semantic_search",
        "clarification":      "run_semantic_search",
        "preference_capture": "run_preference_extractor",
        "insight_request":    "run_insight_generator",
        "off_topic":          "build_response",
    }
    target = mapping.get(intent, "build_response")
    logger.debug(f"[route] intent={intent} → {target}")
    return target


# ── NODE 4a: run_semantic_search ──────────────────────────────────

async def run_semantic_search(state: AgentState) -> dict:
    """
    Runs semantic search against Qdrant using the user message as the query.
    """
    logger.debug(f"[run_semantic_search] conversation={state['conversation_id']}")
    chunks = await semantic_search(query=state["user_message"], top_k=5)
    return {
        "retrieved_chunks": chunks,
        "sources": [
            {
                "document_title": c["document_title"],
                "chunk_index": c["chunk_index"],
                "snippet": c["content"][:120],
            }
            for c in chunks
        ],
    }


# ── NODE 4b: run_preference_extractor ────────────────────────────

async def run_preference_extractor(state: AgentState) -> dict:
    """
    Extracts preferences from the user message via LLM, saves to Supabase,
    then also runs semantic search so the response can reference quests.
    """
    logger.debug(f"[run_preference_extractor] conversation={state['conversation_id']}")
    prompt = PREFERENCE_EXTRACTION_PROMPT.format(user_message=state["user_message"])

    extracted: dict = {}
    try:
        result = _llm_structured.invoke(prompt)
        extracted = _parse_json(result.content)
    except Exception as e:
        logger.error(f"[run_preference_extractor] LLM failed: {e}")

    # Fire-and-forget preference save — don't block node
    if extracted and state.get("user_id"):
        asyncio.create_task(
            extract_and_save_preferences(state["user_id"], extracted)
        )

    # Also run semantic search so response can still cite matching quests
    chunks = await semantic_search(query=state["user_message"], top_k=5)

    return {
        "extracted_preferences": extracted,
        "retrieved_chunks": chunks,
        "sources": [
            {
                "document_title": c["document_title"],
                "chunk_index": c["chunk_index"],
                "snippet": c["content"][:120],
            }
            for c in chunks
        ],
    }


# ── NODE 4c: run_insight_generator ───────────────────────────────

async def run_insight_generator(state: AgentState) -> dict:
    """
    Runs a broader semantic search (top_k=8) then asks the LLM
    to synthesise an insight from the retrieved context.
    """
    logger.debug(f"[run_insight_generator] conversation={state['conversation_id']}")
    chunks = await semantic_search(query=state["user_message"], top_k=8)
    context = build_context_string(chunks)
    history_str = format_history_for_prompt(state["history"])

    prompt = INSIGHT_GENERATION_PROMPT.format(
        context=context,
        history=history_str,
        user_message=state["user_message"],
    )

    try:
        result = _llm_prose.invoke(prompt)
        data = _parse_json(result.content)
        return {
            "retrieved_chunks": chunks,
            "insight": data.get("insight", ""),
            "sources": data.get("sources", []),
            "confidence": float(data.get("confidence", 0.0)),
        }
    except Exception as e:
        logger.error(f"[run_insight_generator] failed: {e}")
        return {"retrieved_chunks": chunks, "insight": None}


# ── NODE 5: build_response ────────────────────────────────────────

async def build_response(state: AgentState) -> dict:
    """
    Builds the final LLM response from retrieved context + history.
    - Off-topic / injections → polite redirect, no LLM call needed.
    - Insight intent → re-use the pre-generated insight string.
    - Quest search / clarification → QUEST_SEARCH_PROMPT with full context.
    - If safety already failed once, appends rewrite_instruction to prompt.
    """
    logger.debug(f"[build_response] conversation={state['conversation_id']}")
    intent = state.get("intent", "off_topic")

    # Short-circuit for off_topic / injection
    if intent == "off_topic" or state.get("injection_detected"):
        draft = (
            "I'm here to help you explore job quests and hiring opportunities. "
            "Could you ask me something about available quests, requirements, "
            "or how to find roles that match your skills?"
        )
        return {"draft_response": draft, "confidence": 1.0}

    # Short-circuit if insight was already generated
    if state.get("insight"):
        return {"draft_response": state["insight"]}

    # Build context and history strings
    context = build_context_string(state.get("retrieved_chunks", []))
    history_str = format_history_for_prompt(state["history"])

    # Fetch candidate profile for personalisation
    profile_str = "No profile data yet"
    if state.get("user_id"):
        try:
            from src.db.supabase import supabase_client
            row = await supabase_client.fetchrow(
                "SELECT * FROM candidate_profiles WHERE user_id = $1",
                state["user_id"],
            )
            if row:
                p = dict(row)
                profile_str = (
                    f"Tech stack: {', '.join(p.get('tech_stack') or []) or 'unknown'} | "
                    f"Preferred roles: {', '.join(p.get('preferred_roles') or []) or 'unknown'} | "
                    f"Experience: {p.get('experience_years') or 'unknown'} years"
                )
        except Exception as e:
            logger.error(f"[build_response] profile fetch failed: {e}")

    prompt = QUEST_SEARCH_PROMPT.format(
        context=context,
        candidate_profile=profile_str,
        history=history_str,
        user_message=state["user_message"],
    )

    # Append rewrite instruction if safety triggered on a previous pass
    if state.get("rewrite_instruction"):
        prompt += f"\n\nIMPORTANT: {state['rewrite_instruction']}"

    try:
        result = _llm_prose.invoke(prompt)
        data = _parse_json(result.content)
        return {
            "draft_response": data.get("answer", ""),
            "sources": data.get("sources", state.get("sources", [])),
            "confidence": float(data.get("confidence", 0.5)),
        }
    except Exception as e:
        logger.error(f"[build_response] failed: {e}")
        return {
            "draft_response": (
                "I encountered an issue finding relevant information. Please try again."
            ),
            "confidence": 0.0,
        }


# ── NODE 6: safety_guard ──────────────────────────────────────────

async def safety_guard(state: AgentState) -> dict:
    """
    Checks draft_response for safety violations.
    - Pass → promotes draft to final_response.
    - Fail (first attempt) → sets rewrite_instruction for build_response retry.
    - Fail (second attempt) → returns a hardcoded safe fallback.
    """
    logger.debug(f"[safety_guard] conversation={state['conversation_id']}")
    result = check_safety(state.get("draft_response", ""))

    if result["passed"]:
        logger.debug("[safety_guard] passed")
        return {
            "safety_passed": True,
            "final_response": state["draft_response"],
        }

    retries = state.get("safety_retries", 0)
    logger.warning(
        f"[safety_guard] FAILED attempt={retries + 1} "
        f"violation={result.get('violation')}"
    )

    if retries >= 1:
        # Second failure — return a hardcoded safe fallback
        return {
            "safety_passed": False,
            "final_response": (
                "I can help you explore job quests and hiring requirements. "
                "What would you like to know about available opportunities?"
            ),
        }

    return {
        "safety_passed": False,
        "rewrite_instruction": result["rewrite_instruction"],
        "safety_retries": retries + 1,
    }


# ── NODE 7: write_memory ──────────────────────────────────────────

from src.services.message_service import save_assistant_message
from src.services.insight_service import save_conversation_insight

async def write_memory(state: AgentState) -> dict:
    """
    Saves the assistant response to Supabase.

    The user message was already saved in the API endpoint
    BEFORE the agent ran — do not save it again here.

    Also saves to the insights table if:
    - intent was insight_request
    - an insight was generated
    - confidence >= 0.7
    """

    # Save assistant message with full metadata
    save_assistant_message(
        conversation_id=state["conversation_id"],
        content=state.get("final_response", ""),
        sources=state.get("sources", []),
        confidence=state.get("confidence"),
        reasoning=state.get("reasoning"),
    )

    # Conditionally save insight to insights table
    if (
        state.get("intent") == "insight_request"
        and state.get("insight")
        and (state.get("confidence") or 0.0) >= 0.7
    ):
        await save_conversation_insight(
            insight_text=state["insight"],
            sources=state.get("sources", []),
            confidence=state["confidence"],
        )

    return {}
