"""
Bias Mitigation / Fairness Monitor
==================================
Addresses R4 (algorithmic bias & fairness). Two design decisions matter here:

1. The adaptivity algorithm (personalization.py) only ever conditions on
   *behavioural* signals (correctness, response time) - it never reads
   `cohort` or any demographic-like attribute, so cohort membership cannot
   directly bias a learner's difficulty curve or feedback.

2. `cohort` is still collected (optionally, non-sensitive e.g. "team-A") so
   that this module can *audit* outcomes across groups after the fact and
   surface disparities to instructors/admins - detecting disparate impact is
   only possible if outcomes are compared across groups, even though the
   model itself is group-blind.

This is a descriptive fairness monitor, not an automated corrective action:
flagging is deliberately left to a human (the instructor dashboard), since
automatically re-weighting outcomes without human review is itself an
ethical risk.
"""
from statistics import mean
from typing import List, Dict

DISPARITY_FLAG_THRESHOLD = 0.15  # absolute mastery-score gap that gets flagged


def audit_cohort_fairness(rows: List[Dict]) -> List[Dict]:
    """
    rows: list of {"cohort": str, "mastery_score": float, "attempts_count": int}
    Returns per-cohort summary stats plus a `flag` indicating whether that
    cohort's average mastery deviates from the overall average by more than
    the threshold (a simple disparate-impact-style signal for instructors to
    investigate further, not a conclusion of bias on its own).
    """
    by_cohort: Dict[str, List[float]] = {}
    for row in rows:
        cohort = row.get("cohort") or "unspecified"
        by_cohort.setdefault(cohort, []).append(row["mastery_score"])

    if not by_cohort:
        return []

    overall_avg = mean(v for values in by_cohort.values() for v in values)

    summary = []
    for cohort, values in sorted(by_cohort.items()):
        cohort_avg = mean(values)
        gap = round(cohort_avg - overall_avg, 4)
        summary.append({
            "cohort": cohort,
            "learner_count": len(values),
            "avg_mastery": round(cohort_avg, 4),
            "deviation_from_overall": gap,
            "flag": abs(gap) >= DISPARITY_FLAG_THRESHOLD,
        })
    return summary
