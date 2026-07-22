from backend.ai_engine.personalization import (
    update_mastery, difficulty_for_mastery, MASTERY_EMA_ALPHA,
)
from backend.ai_engine.llm_client import chat_complete
from backend.ai_engine.scenario_generator import generate_scenario
from backend.ai_engine.mastery_models import bkt_update


def test_mastery_increases_on_correct_answer():
    update = update_mastery(current_mastery=0.3, current_streak=0, correct=True)
    assert update.new_mastery > 0.3
    assert update.new_streak == 1


def test_mastery_decreases_on_incorrect_answer():
    update = update_mastery(current_mastery=0.6, current_streak=2, correct=False)
    assert update.new_mastery < 0.6
    assert update.new_streak == 0


def test_mastery_bounded_between_0_and_1():
    high = update_mastery(current_mastery=0.99, current_streak=5, correct=True)
    low = update_mastery(current_mastery=0.01, current_streak=0, correct=False)
    assert 0.0 <= high.new_mastery <= 1.0
    assert 0.0 <= low.new_mastery <= 1.0


def test_difficulty_recommendation_targets_zpd_stretch():
    # A novice (low mastery) should not be thrown at max difficulty.
    assert difficulty_for_mastery(0.0) < 5
    # An expert should be recommended the hardest available content.
    assert difficulty_for_mastery(1.0) == 5
    # Recommendation should be monotonic in mastery.
    assert difficulty_for_mastery(0.8) >= difficulty_for_mastery(0.2)


def test_llm_client_falls_back_without_api_key(monkeypatch):
    from backend import config
    monkeypatch.setattr(config.settings, "anthropic_api_key", "")
    result = chat_complete("system", "user", fallback_text="fallback message")
    assert result.fallback is True
    assert result.text == "fallback message"


def test_scenario_generator_fallback_produces_valid_shape(monkeypatch):
    from backend import config
    monkeypatch.setattr(config.settings, "anthropic_api_key", "")
    scenario = generate_scenario(skill="data_privacy", difficulty=3)
    assert isinstance(scenario["prompt"], str) and scenario["prompt"]
    assert len(scenario["options"]) == 4
    assert 0 <= scenario["correct_index"] < len(scenario["options"])
    assert scenario["generated_by_ai"] is False


# --- BKT: second mastery-estimation technique, compared against EMA for R1 ---

def test_bkt_mastery_increases_on_correct_answer():
    update = bkt_update(prior_mastery=0.3, correct=True)
    assert update.new_mastery > 0.3


def test_bkt_mastery_decreases_on_incorrect_answer():
    update = bkt_update(prior_mastery=0.6, correct=False)
    assert update.new_mastery < 0.6


def test_bkt_mastery_bounded_between_0_and_1():
    high = bkt_update(prior_mastery=0.99, correct=True)
    low = bkt_update(prior_mastery=0.01, correct=False)
    assert 0.0 <= high.new_mastery <= 1.0
    assert 0.0 <= low.new_mastery <= 1.0


def test_bkt_never_fully_resets_to_zero_due_to_transit():
    # Even a wrong answer at very low mastery should not go to exactly 0,
    # because the learning-transition step always leaves some residual probability.
    update = bkt_update(prior_mastery=0.05, correct=False)
    assert update.new_mastery > 0.0


def test_ema_and_bkt_agree_on_direction_of_change():
    # Both techniques should move in the same direction for the same evidence,
    # even though their magnitudes differ - this is the basic sanity check
    # before comparing them empirically on real attempt data.
    ema = update_mastery(current_mastery=0.5, current_streak=0, correct=True)
    bkt = bkt_update(prior_mastery=0.5, correct=True)
    assert ema.new_mastery > 0.5
    assert bkt.new_mastery > 0.5
