from backend.ethics.bias_mitigation import audit_cohort_fairness, DISPARITY_FLAG_THRESHOLD


def test_no_flag_when_cohorts_are_similar():
    rows = [
        {"cohort": "team-a", "mastery_score": 0.6},
        {"cohort": "team-b", "mastery_score": 0.62},
    ]
    summary = audit_cohort_fairness(rows)
    assert all(not r["flag"] for r in summary)


def test_flag_raised_when_cohort_diverges_beyond_threshold():
    rows = [
        {"cohort": "team-a", "mastery_score": 0.9},
        {"cohort": "team-a", "mastery_score": 0.9},
        {"cohort": "team-b", "mastery_score": 0.9 - DISPARITY_FLAG_THRESHOLD - 0.2},
    ]
    summary = audit_cohort_fairness(rows)
    flagged = {r["cohort"] for r in summary if r["flag"]}
    assert "team-b" in flagged


def test_empty_input_returns_empty_summary():
    assert audit_cohort_fairness([]) == []


def test_unspecified_cohort_grouped_together():
    rows = [{"cohort": None, "mastery_score": 0.5}, {"cohort": None, "mastery_score": 0.7}]
    summary = audit_cohort_fairness(rows)
    assert len(summary) == 1
    assert summary[0]["cohort"] == "unspecified"
    assert summary[0]["learner_count"] == 2
