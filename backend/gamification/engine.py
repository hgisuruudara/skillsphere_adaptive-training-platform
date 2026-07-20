"""
Gamification Engine
====================
Implements the "Rules / Progression / Rewards" box of the architecture diagram.
Pure, deterministic, framework-agnostic scoring logic so it can be unit tested
independently of the API layer or the AI Engine.
"""
import math
from dataclasses import dataclass, field
from typing import List

BASE_POINTS_PER_DIFFICULTY = 20   # points for a correct answer at difficulty 1
SPEED_BONUS_THRESHOLD_MS = 8000   # answers faster than this earn a speed bonus
SPEED_BONUS_POINTS = 10
STREAK_BONUS_STEP = 3             # every N-in-a-row correct answers grants a bonus
STREAK_BONUS_POINTS = 15


@dataclass
class ScoringResult:
    points_awarded: int
    new_total_points: int
    new_level: int
    level_up: bool
    new_badges: List[str] = field(default_factory=list)


def level_for_points(total_points: int) -> int:
    """Level curve: level N requires N^2 * 100 points (classic RPG-style curve)."""
    return max(1, int(math.sqrt(total_points / 100)) + 1)


def compute_points(difficulty: int, correct: bool, response_time_ms: int, correct_streak: int) -> int:
    if not correct:
        return 0
    points = BASE_POINTS_PER_DIFFICULTY * max(1, difficulty)
    if response_time_ms and response_time_ms <= SPEED_BONUS_THRESHOLD_MS:
        points += SPEED_BONUS_POINTS
    if correct_streak > 0 and correct_streak % STREAK_BONUS_STEP == 0:
        points += STREAK_BONUS_POINTS
    return points


def evaluate_badges(existing_codes: set, *, is_first_attempt: bool, correct_streak: int,
                     mastery_score: float, distinct_days_active: int) -> List[str]:
    """Rule-based badge unlocks. Returns list of (code, name) pairs newly earned."""
    earned = []

    def award(code, name):
        if code not in existing_codes:
            earned.append((code, name))

    if is_first_attempt:
        award("first_steps", "First Steps")
    if correct_streak >= 3:
        award("quick_learner", "Quick Learner (3-streak)")
    if correct_streak >= 5:
        award("perfectionist", "Perfectionist (5-streak)")
    if mastery_score >= 0.85:
        award("skill_master", "Skill Master")
    if distinct_days_active >= 3:
        award("consistent_learner", "Consistent Learner")
    return earned


def score_attempt(*, total_points_before: int, difficulty: int, correct: bool,
                   response_time_ms: int, correct_streak_after: int) -> ScoringResult:
    points = compute_points(difficulty, correct, response_time_ms, correct_streak_after)
    new_total = total_points_before + points
    old_level = level_for_points(total_points_before)
    new_level = level_for_points(new_total)
    return ScoringResult(
        points_awarded=points,
        new_total_points=new_total,
        new_level=new_level,
        level_up=new_level > old_level,
    )
