"""
Scenario Generator
==================
"Retrieve / Generate" arrow into the Training Content Repository box: given a
learner's mastery level and a target skill, either retrieves a fitting
pre-authored quest, or asks the LLM engine to generate a fresh multiple-choice
workplace scenario tailored to the learner's level. Falls back to a small
template bank when no LLM key is configured, so scenario generation is never
a hard dependency for running the demo.
"""
import json
import random
import re
from typing import Optional

from backend.ai_engine.llm_client import chat_complete

_FALLBACK_BANK = {
    "workplace_safety": [
        "A colleague is about to lift a heavy box using their back instead of their legs. What should you do?",
        "You notice a spill on the warehouse floor with no warning sign. What is the correct first action?",
        "An emergency exit is partially blocked by stacked pallets. What is the appropriate response?",
    ],
    "customer_service": [
        "A customer is raising their voice about a late delivery. What is the best de-escalation response?",
        "A client asks for a refund outside of policy. How do you respond while preserving the relationship?",
        "A customer message contains conflicting complaints. What is the best first step?",
    ],
    "data_privacy": [
        "A colleague asks you to email a spreadsheet of customer personal data to their personal account. What do you do?",
        "You discover a shared drive with unrestricted access to employee salary data. What is the correct escalation?",
        "A vendor requests customer data 'just to test integration'. What should you check first?",
    ],
}

_GENERIC_OPTIONS = [
    "Follow documented policy and escalate to the appropriate owner",
    "Address it immediately yourself without informing anyone",
    "Ignore it since it is not directly your responsibility",
    "Wait to see if someone else notices and handles it",
]


def _slugify(skill: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", skill.lower()).strip("_")


def generate_scenario(*, skill: str, difficulty: int, topic: Optional[str] = None) -> dict:
    """
    Returns a dict shaped like a Quest: {prompt, options, correct_index, generated_by_ai}.
    """
    system_prompt = (
        "You are an instructional designer creating corporate training scenarios. "
        "Respond ONLY with strict JSON: "
        '{"prompt": str, "options": [str, str, str, str], "correct_index": int}. '
        "correct_index is 0-based and must point to the option representing policy-"
        "compliant, professional best practice. Keep prompt under 40 words."
    )
    user_prompt = (
        f"Skill: {skill}\n"
        f"Topic focus: {topic or skill}\n"
        f"Target difficulty: {difficulty}/5 (5 = most nuanced/ambiguous scenario)\n"
        "Write one realistic corporate workplace scenario question with 4 answer options."
    )
    fallback_prompt = _fallback_prompt(skill)
    result = chat_complete(system_prompt, user_prompt, fallback_text=fallback_prompt, max_tokens=400)

    if not result.fallback:
        parsed = _try_parse_json(result.text)
        if parsed:
            return {**parsed, "generated_by_ai": True}

    # Fallback path (no LLM configured, or LLM response failed to parse)
    options = _GENERIC_OPTIONS.copy()
    random.shuffle(options)
    correct_index = options.index(_GENERIC_OPTIONS[0])
    return {
        "prompt": result.text if not result.fallback else fallback_prompt,
        "options": options,
        "correct_index": correct_index,
        "generated_by_ai": False,
    }


def _fallback_prompt(skill: str) -> str:
    key = _slugify(skill)
    bank = _FALLBACK_BANK.get(key) or _FALLBACK_BANK["workplace_safety"]
    return random.choice(bank)


def _try_parse_json(text: str) -> Optional[dict]:
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group(0) if match else text)
        if {"prompt", "options", "correct_index"} <= data.keys() and len(data["options"]) >= 2:
            return data
    except Exception:
        return None
    return None
