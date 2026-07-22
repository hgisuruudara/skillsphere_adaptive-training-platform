from backend.ai_engine.personalization import fixed_progression_difficulty


def test_pooled_stdev_matches_hand_calculation():
    # Deferred import: backend.analytics.reporting imports backend.models at
    # module level, which must not happen during pytest collection - test_api.py's
    # fixture reloads backend.database (and thus needs backend.models bound to
    # a fresh Base) the first time it runs. Importing eagerly here would cache
    # backend.models against the pre-reload Base and break that isolation.
    from backend.analytics.reporting import _pooled_stdev

    # Two groups with known variance: [1,2,3] (var=1) and [4,6,8] (var=4)
    result = _pooled_stdev([1, 2, 3], [4, 6, 8])
    assert round(result, 4) == round(((2 * 1 + 2 * 4) / 4) ** 0.5, 4)


def test_effect_size_interpretation_thresholds():
    from backend.analytics.reporting import _interpret_effect_size

    assert _interpret_effect_size(0.05) == "negligible"
    assert _interpret_effect_size(0.3) == "small"
    assert _interpret_effect_size(0.6) == "medium"
    assert _interpret_effect_size(1.2) == "large"
    assert _interpret_effect_size(-0.9) == "large"  # magnitude, not sign


def test_fixed_progression_is_non_reactive_to_performance():
    # Unlike difficulty_for_mastery, fixed progression only depends on how
    # many attempts have happened, not on correctness/mastery - this is the
    # defining property of the R3 control-condition baseline.
    assert fixed_progression_difficulty(0) == 1
    assert fixed_progression_difficulty(3) == 4
    assert fixed_progression_difficulty(10) == 5  # capped at MAX_DIFFICULTY
