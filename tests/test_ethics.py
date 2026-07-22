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


def test_synthetic_bias_injection_script_passes():
    """
    Runs the R4 evidence script end-to-end (as a subprocess, exactly how a
    reader would run it) and checks it reports both PASS lines and no FAIL -
    i.e. the fairness monitor correctly leaves a fair scenario unflagged and
    correctly catches a deliberately injected disparity.
    """
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "scripts" / "synthetic_bias_check.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=30)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("PASS:") == 2
    assert "FAIL" not in result.stdout
