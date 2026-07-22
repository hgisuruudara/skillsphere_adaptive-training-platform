#!/usr/bin/env python3
"""
Synthetic Bias-Injection Check (R4 evidence)
=============================================
Addresses the part of Research Question 4 (R4) that asks how ethical/fairness
mitigations can be verified, not just designed. This script does not touch
the running application or database - it feeds two synthetic cohort datasets
directly into the real `audit_cohort_fairness()` function used by the
Instructor Dashboard, and checks that it behaves correctly in both cases:

  Scenario A (fair):     cohorts have similar mastery -> no flag expected.
  Scenario B (injected):  one cohort is deliberately, artificially
                          disadvantaged -> the fairness monitor should catch it.

Run from the repository root:
    python scripts/synthetic_bias_check.py

This is meant to be run and its console output screenshotted/pasted directly
as evidence that the fairness *mitigation* works, not just that it exists in
code (see docs/ETHICS_PRIVACY.md section 3 and
docs/THESIS_MAPPING.md's R4 evidence row).
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ethics.bias_mitigation import audit_cohort_fairness, DISPARITY_FLAG_THRESHOLD  # noqa: E402

random.seed(42)  # reproducible synthetic data across runs


def make_cohort_rows(cohort: str, mean_mastery: float, n: int, spread: float = 0.05) -> list[dict]:
    return [
        {"cohort": cohort, "mastery_score": max(0.0, min(1.0, random.gauss(mean_mastery, spread)))}
        for _ in range(n)
    ]


def print_report(title: str, rows: list[dict]) -> list[dict]:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
    summary = audit_cohort_fairness(rows)
    print(f"{'Cohort':<12} {'Learners':<10} {'Avg Mastery':<14} {'Deviation':<12} {'Flag'}")
    for row in summary:
        deviation_pct = f"{row['deviation_from_overall'] * 100:+.1f}%"
        avg_pct = f"{row['avg_mastery'] * 100:.1f}%"
        flag = "REVIEW" if row["flag"] else "ok"
        print(f"{row['cohort']:<12} {row['learner_count']:<10} {avg_pct:<14} {deviation_pct:<12} {flag}")
    return summary


def main() -> int:
    print(f"Fairness monitor disparity threshold: {DISPARITY_FLAG_THRESHOLD * 100:.0f} percentage points")
    print("(from backend/ethics/bias_mitigation.py::DISPARITY_FLAG_THRESHOLD)")

    # --- Scenario A: fair, no injected disparity ---
    fair_rows = make_cohort_rows("team-alpha", 0.65, 20) + make_cohort_rows("team-beta", 0.68, 20)
    fair_summary = print_report("SCENARIO A - Fair (no injected disparity)", fair_rows)
    fair_flagged = [r["cohort"] for r in fair_summary if r["flag"]]

    # --- Scenario B: one cohort deliberately, artificially disadvantaged ---
    biased_rows = make_cohort_rows("team-alpha", 0.75, 20) + make_cohort_rows("team-beta", 0.40, 20)
    biased_summary = print_report("SCENARIO B - Injected disparity (team-beta artificially disadvantaged)", biased_rows)
    biased_flagged = [r["cohort"] for r in biased_summary if r["flag"]]

    print(f"\n{'=' * 60}\nRESULT\n{'=' * 60}")
    ok = True

    if fair_flagged:
        print(f"UNEXPECTED: Scenario A flagged {fair_flagged} despite no injected disparity.")
        ok = False
    else:
        print("PASS: Scenario A (fair) correctly raised no flags.")

    if "team-beta" in biased_flagged:
        print("PASS: Scenario B correctly flagged 'team-beta' as a disparity requiring review.")
    else:
        print("FAIL: Scenario B did NOT flag the injected disparity - fairness monitor did not catch it.")
        ok = False

    print()
    if ok:
        print("Overall: the fairness monitor correctly distinguishes a fair distribution "
              "from a deliberately injected disparity, on synthetic data outside the "
              "live application.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
