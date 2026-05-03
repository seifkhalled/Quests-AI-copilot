from typing import TypedDict, Optional
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):

    # ── Input ──────────────────────────────────────────────
    conversation_id: str
    user_id: str
    user_message: str

    # ── Context loaded from Redis ──────────────────────────
    # List of last 5 turns as LangChain message objects
    # Each item is HumanMessage or AIMessage
    history: list[BaseMessage]

    # ── Intent detection output ────────────────────────────
    # One of: quest_search | preference_capture |
    #         insight_request | clarification | off_topic
    intent: Optional[str]

    # Flag set to True if injection attempt detected
    injection_detected: bool

    # ── Tool outputs ───────────────────────────────────────
    # Raw chunks returned from Qdrant semantic search
    # Each item: { content, document_title, chunk_index, score }
    retrieved_chunks: list[dict]

    # Preferences extracted from this turn
    # { tech_stack: [], preferred_roles: [], experience_years: int | None }
    extracted_preferences: Optional[dict]

    # Generated insight string (if intent = insight_request)
    insight: Optional[str]

    # ── Response building ──────────────────────────────────
    # Draft answer before safety check
    draft_response: Optional[str]

    # Sources to cite alongside the answer
    # Each: { document_title, chunk_index, snippet }
    sources: list[dict]

    # Confidence score 0.0–1.0
    confidence: Optional[float]

    # ── Safety ─────────────────────────────────────────────
    safety_passed: bool

    # If safety fails, this instruction is injected into the
    # next build_response call to rewrite the answer
    rewrite_instruction: Optional[str]

    # How many times safety has triggered in this turn (max 1 retry)
    safety_retries: int

    # ── Final output ───────────────────────────────────────
    final_response: Optional[str]
