import logging

from langgraph.graph import StateGraph, END

from src.agent.state import AgentState
from src.agent.nodes import (
    load_context,
    detect_intent,
    route,
    run_semantic_search,
    run_preference_extractor,
    run_insight_generator,
    build_response,
    safety_guard,
    write_memory,
)

logger = logging.getLogger(__name__)


def safety_route(state: AgentState) -> str:
    """
    Conditional edge after safety_guard:
    - passed=True         → write_memory
    - passed=False, retries < 1  → build_response (rewrite pass)
    - passed=False, retries >= 1 → write_memory with safe fallback
    """
    if state.get("safety_passed"):
        return "write_memory"
    if state.get("safety_retries", 0) < 1:
        return "build_response"
    return "write_memory"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────
    graph.add_node("load_context",             load_context)
    graph.add_node("detect_intent",            detect_intent)
    graph.add_node("run_semantic_search",      run_semantic_search)
    graph.add_node("run_preference_extractor", run_preference_extractor)
    graph.add_node("run_insight_generator",    run_insight_generator)
    graph.add_node("build_response",           build_response)
    graph.add_node("safety_guard",             safety_guard)
    graph.add_node("write_memory",             write_memory)

    # ── Entry point ────────────────────────────────────────
    graph.set_entry_point("load_context")

    # ── Fixed edges ────────────────────────────────────────
    graph.add_edge("load_context", "detect_intent")

    # ── Conditional routing after intent detection ─────────
    graph.add_conditional_edges(
        "detect_intent",
        route,
        {
            "run_semantic_search":      "run_semantic_search",
            "run_preference_extractor": "run_preference_extractor",
            "run_insight_generator":    "run_insight_generator",
            "build_response":           "build_response",
        },
    )

    # ── All tool nodes converge at build_response ──────────
    graph.add_edge("run_semantic_search",      "build_response")
    graph.add_edge("run_preference_extractor", "build_response")
    graph.add_edge("run_insight_generator",    "build_response")

    # ── build_response always goes to safety_guard ─────────
    graph.add_edge("build_response", "safety_guard")

    # ── Conditional safety routing ─────────────────────────
    graph.add_conditional_edges(
        "safety_guard",
        safety_route,
        {
            "write_memory":   "write_memory",
            "build_response": "build_response",
        },
    )

    # ── write_memory is the terminal node ──────────────────
    graph.add_edge("write_memory", END)

    return graph.compile()


# Compiled once at import time — reused across all requests
agent_graph = build_graph()
logger.info("LangGraph agent compiled successfully")
