"""
LLM Client
==========
Thin wrapper around the Claude Messages API (Anthropic) used by the
LLM-Based AI Engine box in the architecture diagram (personalization /
adaptive feedback / scenario generation).

Design goal: the rest of the codebase (and the thesis demo) must run with
*zero* external dependencies or API keys. When `settings.llm_enabled` is
False (no ANTHROPIC_API_KEY configured), every call transparently falls back
to a deterministic, template-based generator (`fallback=True` in the result)
so behaviour stays reproducible for grading/evaluation and works fully
offline.
"""
from dataclasses import dataclass

from backend.config import settings


@dataclass
class LLMResult:
    text: str
    fallback: bool  # True if produced by the offline heuristic, not a real LLM call


def _get_client():
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def chat_complete(system_prompt: str, user_prompt: str, *, fallback_text: str,
                   max_tokens: int = 300) -> LLMResult:
    """
    Calls Claude if configured; otherwise returns `fallback_text`.
    Any runtime/API error also degrades gracefully to the fallback rather than
    crashing the training session - reliability matters more than a single
    generation for a learner mid-quest.
    """
    if not settings.llm_enabled:
        return LLMResult(text=fallback_text, fallback=True)

    try:
        client = _get_client()
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            return LLMResult(text=fallback_text, fallback=True)
        return LLMResult(text=text, fallback=False)
    except Exception:
        return LLMResult(text=fallback_text, fallback=True)
