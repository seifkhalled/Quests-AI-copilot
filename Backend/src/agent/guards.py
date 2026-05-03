import json
import logging
from langchain_groq import ChatGroq
from src.agent.prompts import SAFETY_CHECK_PROMPT
from src.core.config import settings

logger = logging.getLogger(__name__)

# Single LLM instance for safety checks — temperature=0 for determinism
_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=settings.GROQ_AGENT_API_KEY,
)


def check_safety(draft_response: str) -> dict:
    """
    Runs the safety check prompt against the draft response.
    Returns { passed: bool, violation: str|None, rewrite_instruction: str|None }
    Never raises — always returns a safe dict even on LLM failure.
    """
    prompt = SAFETY_CHECK_PROMPT.format(draft_response=draft_response)
    try:
        result = _llm.invoke(prompt)
        # Strip markdown code fences if the model wrapped the JSON
        content = result.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(content)
        logger.debug(f"Safety check passed={data.get('passed')}")
        return {
            "passed": bool(data.get("passed", False)),
            "violation": data.get("violation"),
            "rewrite_instruction": data.get("rewrite_instruction"),
        }
    except Exception as e:
        logger.error(f"Safety check raised an exception: {e}")
        return {
            "passed": False,
            "violation": "Safety check could not be completed",
            "rewrite_instruction": (
                "Respond with a polite message saying you cannot help with that"
            ),
        }
