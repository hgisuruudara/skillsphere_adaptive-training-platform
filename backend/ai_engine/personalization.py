"""
Personalization & Adaptivity
============================
Implements the technical core of Research Question 1 (R1): AI-driven
personalization and adaptivity mechanisms.

Two mechanisms are implemented:

1. Mastery estimation - an Exponential Moving Average (EMA) update over
   correctness, a lightweight stand-in for IRT/Bayesian Knowledge Tracing that
   is transparent and explainable (important for the ethics/fairness
   objective, R4 - a black-box model would be harder to audit).

2. Difficulty recommendation - grounded in Vygotsky's Zone of Proximal
   Development (ZPD): the next quest should be *just* above the learner's
   current mastery, not the easiest or hardest available item. This keeps the
   learner in a state of productive struggle, which is also the mechanism
   Csikszentmihalyi's Flow Theory identifies as necessary for engagement
   (challenge-skill balance).
"""
from dataclasses import dataclass
from typing import Optional

MASTERY_EMA_ALPHA = 0.3          # weight given to the newest attempt
DEFAULT_INITIAL_MASTERY = 0.3
MIN_DIFFICULTY, MAX_DIFFICULTY = 1, 5


@dataclass
class MasteryUpdate:
    new_mastery: float
    new_streak: int
    recommended_difficulty: int


def update_mastery(*, current_mastery: float, current_streak: int, correct: bool) -> MasteryUpdate:
    observed = 1.0 if correct else 0.0
    new_mastery = current_mastery + MASTERY_EMA_ALPHA * (observed - current_mastery)
    new_mastery = round(min(max(new_mastery, 0.0), 1.0), 4)
    new_streak = current_streak + 1 if correct else 0

    recommended_difficulty = difficulty_for_mastery(new_mastery)
    return MasteryUpdate(new_mastery=new_mastery, new_streak=new_streak,
                          recommended_difficulty=recommended_difficulty)


def difficulty_for_mastery(mastery: float) -> int:
    """
    Maps mastery (0..1) onto a 1..5 difficulty band, deliberately targeting a
    level *slightly above* current mastery (the ZPD 'stretch zone') rather
    than the level that matches mastery exactly.
    """
    band = min(MAX_DIFFICULTY, MIN_DIFFICULTY + int(mastery * 5))
    stretched = min(MAX_DIFFICULTY, band + 1)
    return stretched


def fixed_progression_difficulty(attempts_count: int) -> int:
    """
    Traditional, non-adaptive difficulty progression: advances by a fixed
    schedule (module order) after each attempt, regardless of correctness or
    mastery. This is the R3 control-condition baseline compared against the
    ZPD-based difficulty_for_mastery() used for the treatment condition -
    see docs/EVALUATION_FRAMEWORK.md section 1.
    """
    return min(MAX_DIFFICULTY, MIN_DIFFICULTY + attempts_count)


def build_feedback_prompt(*, learner_display_name: str, skill: str, correct: bool,
                           mastery_score: float, difficulty: int, prompt_text: str,
                           previous_mistake: Optional[str] = None) -> tuple[str, str]:
    """
    Builds the (system_prompt, user_prompt) pair sent to the LLM for adaptive
    feedback. `previous_mistake` - the prompt text of the learner's most recent
    incorrect attempt on this same skill, if any - lets feedback reference a
    specific past error rather than only a difficulty number, giving R1's
    personalization a second, independent dimension beyond difficulty.
    """
    system_prompt = (
        "You are an encouraging, concise corporate-training coach embedded in a "
        "gamified learning platform. Give personalized, actionable feedback in "
        "2-3 sentences. Never mention that you are an AI model. Do not repeat "
        "the question verbatim. Adapt tone to the learner's current mastery: "
        "be more supportive at low mastery, more challenging at high mastery. "
        "If a past mistake is provided, briefly connect today's feedback to it "
        "(e.g. noting improvement or a recurring pattern) - do not just restate it."
    )
    user_prompt = (
        f"Learner: {learner_display_name}\n"
        f"Skill being trained: {skill}\n"
        f"Current mastery estimate: {mastery_score:.2f} (0=novice, 1=expert)\n"
        f"Question difficulty: {difficulty}/5\n"
        f"Question: {prompt_text}\n"
        f"Learner answered: {'correctly' if correct else 'incorrectly'}\n"
    )
    if previous_mistake:
        user_prompt += f"Most recent past mistake on this skill: \"{previous_mistake}\"\n"
    user_prompt += (
        "Write feedback that reinforces the correct concept and suggests what "
        "to focus on next."
    )
    return system_prompt, user_prompt


def fallback_feedback(*, correct: bool, skill: str, mastery_score: float, difficulty: int,
                       previous_mistake: Optional[str] = None) -> str:
    """Deterministic feedback used when no LLM is configured."""
    if correct:
        if previous_mistake:
            base = (f"Nice work - this builds on the kind of scenario that tripped you up "
                    f"before, and you handled it correctly this time.")
        elif mastery_score >= 0.8:
            base = (f"Excellent - you're operating at expert level on {skill}. "
                    f"Ready for a harder scenario (difficulty {min(5, difficulty + 1)}).")
        else:
            base = (f"Correct! Your {skill} mastery is climbing ({mastery_score:.0%}). "
                    f"Keep going to unlock tougher scenarios.")
        return base

    if previous_mistake:
        return (f"This is similar to a {skill} scenario you found difficult before - "
                f"focus on the same core policy or principle rather than the surface details.")
    if mastery_score < 0.4:
        return (f"Not quite - {skill} needs more practice. Review the fundamentals "
                f"before the next attempt; the next question will be a bit easier.")
    return (f"Close, but not correct. Your overall {skill} mastery is still solid "
            f"({mastery_score:.0%}) - review this concept and try a similar question.")
