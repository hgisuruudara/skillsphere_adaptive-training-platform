from backend.gamification.engine import (
    compute_points, level_for_points, score_attempt, evaluate_badges,
    BASE_POINTS_PER_DIFFICULTY, SPEED_BONUS_POINTS, STREAK_BONUS_POINTS,
)


def test_no_points_for_incorrect_answer():
    assert compute_points(difficulty=3, correct=False, response_time_ms=1000, correct_streak=0) == 0


def test_base_points_scale_with_difficulty():
    assert compute_points(difficulty=1, correct=True, response_time_ms=99999, correct_streak=1) == BASE_POINTS_PER_DIFFICULTY
    assert compute_points(difficulty=3, correct=True, response_time_ms=99999, correct_streak=1) == BASE_POINTS_PER_DIFFICULTY * 3


def test_speed_bonus_applied_when_fast():
    slow = compute_points(difficulty=1, correct=True, response_time_ms=99999, correct_streak=1)
    fast = compute_points(difficulty=1, correct=True, response_time_ms=1000, correct_streak=1)
    assert fast == slow + SPEED_BONUS_POINTS


def test_streak_bonus_every_third_correct():
    points_at_3 = compute_points(difficulty=1, correct=True, response_time_ms=99999, correct_streak=3)
    points_at_2 = compute_points(difficulty=1, correct=True, response_time_ms=99999, correct_streak=2)
    assert points_at_3 == points_at_2 + STREAK_BONUS_POINTS


def test_level_curve_monotonic_and_starts_at_1():
    assert level_for_points(0) == 1
    assert level_for_points(100) >= 1
    assert level_for_points(10000) > level_for_points(100)


def test_score_attempt_reports_level_up():
    result = score_attempt(total_points_before=90, difficulty=5, correct=True,
                            response_time_ms=1000, correct_streak_after=1)
    assert result.new_total_points > 90
    assert result.new_level >= level_for_points(90)


def test_badges_first_attempt_and_streaks():
    earned = evaluate_badges(set(), is_first_attempt=True, correct_streak=5,
                              mastery_score=0.9, distinct_days_active=4)
    codes = {code for code, _ in earned}
    assert codes == {"first_steps", "quick_learner", "perfectionist", "skill_master", "consistent_learner"}


def test_badges_not_re_awarded():
    earned = evaluate_badges({"first_steps"}, is_first_attempt=True, correct_streak=0,
                              mastery_score=0.1, distinct_days_active=1)
    assert earned == []
