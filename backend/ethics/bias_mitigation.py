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

A cohort is flagged only when its mastery gap is BOTH practically significant
(deviates from the overall average by at least DISPARITY_FLAG_THRESHOLD) AND
statistically significant (Welch's t-test p-value below P_VALUE_THRESHOLD
against the rest of the population) - requiring both is more defensible than
a fixed percentage-point cutoff alone, since a small sample can produce a
large-looking gap by chance. The t-test is implemented from scratch with the
standard library only (no scipy), to keep the project's dependency footprint
- and therefore its Windows-install reliability - unchanged.
"""
import math
from statistics import mean, variance
from typing import List, Dict, Optional

DISPARITY_FLAG_THRESHOLD = 0.15  # absolute mastery-score gap that gets flagged
P_VALUE_THRESHOLD = 0.05         # standard significance level for the t-test


def audit_cohort_fairness(rows: List[Dict]) -> List[Dict]:
    """
    rows: list of {"cohort": str, "mastery_score": float, "attempts_count": int}
    Returns per-cohort summary stats plus a `flag` indicating whether that
    cohort's average mastery deviates from the overall average by more than
    the threshold AND that deviation is statistically significant against
    the rest of the population (Welch's t-test) - a disparate-impact-style
    signal for instructors to investigate further, not a conclusion of bias
    on its own.
    """
    by_cohort: Dict[str, List[float]] = {}
    for row in rows:
        cohort = row.get("cohort") or "unspecified"
        by_cohort.setdefault(cohort, []).append(row["mastery_score"])

    if not by_cohort:
        return []

    all_values = [v for values in by_cohort.values() for v in values]
    overall_avg = mean(all_values)

    summary = []
    for cohort, values in sorted(by_cohort.items()):
        cohort_avg = mean(values)
        gap = round(cohort_avg - overall_avg, 4)

        rest = [v for c, vals in by_cohort.items() if c != cohort for v in vals]
        p_value = welch_t_test_pvalue(values, rest)

        practically_significant = abs(gap) >= DISPARITY_FLAG_THRESHOLD
        statistically_significant = p_value is not None and p_value < P_VALUE_THRESHOLD
        # If a t-test couldn't be computed (too few samples in one group),
        # fall back to the practical-significance check alone, conservatively
        # noting that statistical confirmation wasn't possible.
        flag = practically_significant and (statistically_significant or p_value is None)

        summary.append({
            "cohort": cohort,
            "learner_count": len(values),
            "avg_mastery": round(cohort_avg, 4),
            "deviation_from_overall": gap,
            "p_value": p_value,
            "flag": flag,
        })
    return summary


def welch_t_test_pvalue(sample_a: List[float], sample_b: List[float]) -> Optional[float]:
    """
    Two-sample Welch's t-test (unequal variances assumed), returning the
    two-tailed p-value, or None if either sample has fewer than 2 points
    (variance - and therefore a t-test - is undefined).
    """
    n1, n2 = len(sample_a), len(sample_b)
    if n1 < 2 or n2 < 2:
        return None

    m1, m2 = mean(sample_a), mean(sample_b)
    v1, v2 = variance(sample_a), variance(sample_b)

    se_squared = v1 / n1 + v2 / n2
    if se_squared <= 0:
        return None  # no variance in either group - not a meaningful test

    t_stat = (m1 - m2) / math.sqrt(se_squared)
    df = se_squared ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))

    x = df / (df + t_stat ** 2)
    p_value = _regularized_incomplete_beta(df / 2, 0.5, x)
    return round(p_value, 6)


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """Standard numerical implementation (continued fraction) of I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - log_beta)

    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def _beta_continued_fraction(a: float, b: float, x: float, max_iter: int = 200, eps: float = 3e-10) -> float:
    """Lentz's algorithm for the continued fraction used by the incomplete beta function."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break

    return h
