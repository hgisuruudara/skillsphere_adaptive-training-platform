"""
Analytics Reporting
====================
Implements the metrics groundwork for Research Question 5 (R5): what should
be measured to evaluate an AI-enhanced gamified training system. Three
categories are surfaced, matching the standard engagement / learning /
fairness triad used in the evaluation framework (see docs/EVALUATION_FRAMEWORK.md):

  1. Engagement metrics   - attempts volume, active learners over time
  2. Performance metrics  - accuracy, response time, mastery distribution
  3. Fairness metrics     - cross-cohort disparity (delegates to ethics module)
"""
import datetime as dt
from collections import defaultdict
from statistics import mean, stdev

from sqlalchemy.orm import Session

from backend import models
from backend.ethics.bias_mitigation import audit_cohort_fairness
from backend.ai_engine.personalization import DEFAULT_INITIAL_MASTERY


def build_dashboard_metrics(db: Session) -> dict:
    learners = db.query(models.Learner).all()
    attempts = db.query(models.Attempt).all()
    events = db.query(models.EngagementEvent).all()
    skills = db.query(models.SkillMastery).all()

    total_learners = len(learners)
    consented_learners = sum(1 for l in learners if l.consent_given and not l.erased_at)
    total_attempts = len(attempts)
    overall_accuracy = round(mean([1.0 if a.correct else 0.0 for a in attempts]), 4) if attempts else 0.0
    avg_response_time_ms = round(mean([a.response_time_ms for a in attempts if a.response_time_ms]), 1) if attempts else 0.0

    cutoff = dt.datetime.utcnow() - dt.timedelta(days=7)
    active_last_7_days = len({e.learner_id for e in events if e.timestamp >= cutoff})

    engagement_by_day = _engagement_by_day(events, days=14)

    learner_cohort = {l.id: l.cohort for l in learners}
    fairness_rows = [
        {"cohort": learner_cohort.get(s.learner_id), "mastery_score": s.mastery_score}
        for s in skills
    ]
    fairness_monitor = audit_cohort_fairness(fairness_rows)

    top_learners = sorted(
        ({"id": l.id, "display_name": l.display_name, "points": l.total_points, "level": l.level}
         for l in learners if not l.erased_at),
        key=lambda x: x["points"], reverse=True,
    )[:10]

    technique_comparison = _technique_comparison(skills)

    return {
        "total_learners": total_learners,
        "consented_learners": consented_learners,
        "total_attempts": total_attempts,
        "overall_accuracy": overall_accuracy,
        "avg_response_time_ms": avg_response_time_ms,
        "active_last_7_days": active_last_7_days,
        "engagement_by_day": engagement_by_day,
        "fairness_monitor": fairness_monitor,
        "top_learners": top_learners,
        "technique_comparison": technique_comparison,
    }


def _technique_comparison(skills) -> dict:
    """
    R1 evidence: compares the two independently-computed mastery estimators
    (EMA - drives real difficulty decisions - vs BKT - shadow metric) on the
    same real attempt data. Only includes skill rows with at least one
    attempt, since both estimators start at the same default and are
    otherwise meaningless to compare.
    """
    rows = [s for s in skills if s.attempts_count > 0]
    if not rows:
        return {
            "sample_size": 0, "avg_ema_mastery": None, "avg_bkt_mastery": None,
            "mean_absolute_difference": None, "agreement_rate": None,
        }

    ema_scores = [s.mastery_score for s in rows]
    bkt_scores = [s.mastery_score_bkt for s in rows]
    abs_diffs = [abs(e - b) for e, b in zip(ema_scores, bkt_scores)]
    agreements = [1 for e, b in zip(ema_scores, bkt_scores) if (e >= 0.5) == (b >= 0.5)]

    return {
        "sample_size": len(rows),
        "avg_ema_mastery": round(mean(ema_scores), 4),
        "avg_bkt_mastery": round(mean(bkt_scores), 4),
        "mean_absolute_difference": round(mean(abs_diffs), 4),
        "agreement_rate": round(len(agreements) / len(rows), 4),
    }


def _engagement_by_day(events, days: int) -> list[dict]:
    buckets = defaultdict(lambda: {"attempts": 0, "learners": set()})
    for e in events:
        day = e.timestamp.date().isoformat()
        buckets[day]["attempts"] += 1 if e.event_type == "quest_complete" else 0
        buckets[day]["learners"].add(e.learner_id)

    today = dt.date.today()
    series = []
    for i in range(days - 1, -1, -1):
        day = (today - dt.timedelta(days=i)).isoformat()
        bucket = buckets.get(day, {"attempts": 0, "learners": set()})
        series.append({"date": day, "attempts": bucket["attempts"], "active_learners": len(bucket["learners"])})
    return series


def comparative_study_stats(db: Session) -> dict:
    """
    R3 evidence: compares the treatment (AI-driven) and control (traditional)
    conditions on real attempt data - see docs/EVALUATION_FRAMEWORK.md section 1
    for the protocol (random assignment at consent, condition-branched routes
    in routers/quests.py and routers/gameplay.py). Reports mastery growth rate,
    accuracy, and attempts-per-learner per condition, plus a Cohen's d effect
    size on growth rate (H1 in the evaluation framework).
    """
    learners = db.query(models.Learner).filter(models.Learner.erased_at.is_(None)).all()
    condition_by_learner = {l.id: l.condition for l in learners}

    skills = db.query(models.SkillMastery).filter(models.SkillMastery.attempts_count > 0).all()
    attempts = db.query(models.Attempt).all()

    def group_stats(condition: str) -> dict:
        rows = [s for s in skills if condition_by_learner.get(s.learner_id) == condition]
        learner_ids = {s.learner_id for s in rows}
        growth_rates = [(s.mastery_score - DEFAULT_INITIAL_MASTERY) / s.attempts_count for s in rows]
        group_attempts = [a for a in attempts if condition_by_learner.get(a.learner_id) == condition]
        accuracy = mean([1.0 if a.correct else 0.0 for a in group_attempts]) if group_attempts else None

        return {
            "learner_count": len(learner_ids),
            "avg_mastery_growth_rate": round(mean(growth_rates), 4) if growth_rates else None,
            "overall_accuracy": round(accuracy, 4) if accuracy is not None else None,
            "avg_attempts_per_learner": round(len(group_attempts) / len(learner_ids), 2) if learner_ids else None,
            "_growth_rates": growth_rates,
        }

    control = group_stats("control")
    treatment = group_stats("treatment")

    cohens_d, interpretation = None, None
    c_rates, t_rates = control["_growth_rates"], treatment["_growth_rates"]
    if len(c_rates) >= 2 and len(t_rates) >= 2:
        pooled_std = _pooled_stdev(c_rates, t_rates)
        if pooled_std > 0:
            cohens_d = round((mean(t_rates) - mean(c_rates)) / pooled_std, 4)
            interpretation = _interpret_effect_size(cohens_d)

    control.pop("_growth_rates")
    treatment.pop("_growth_rates")

    return {
        "control": control,
        "treatment": treatment,
        "cohens_d": cohens_d,
        "effect_size_interpretation": interpretation,
        "note": ("Effect size requires at least 2 learners with attempts in each condition. "
                 "Treat this as pilot-scale evidence, not a fully powered study - report "
                 "sample sizes alongside the effect size (see docs/EVALUATION_FRAMEWORK.md section 3)."),
    }


def _pooled_stdev(a: list, b: list) -> float:
    n1, n2 = len(a), len(b)
    s1, s2 = stdev(a), stdev(b)
    pooled_variance = ((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2)
    return pooled_variance ** 0.5


def _interpret_effect_size(d: float) -> str:
    magnitude = abs(d)
    if magnitude < 0.2:
        return "negligible"
    if magnitude < 0.5:
        return "small"
    if magnitude < 0.8:
        return "medium"
    return "large"


def learner_history(db: Session, learner_id: str, limit: int = 20) -> list[dict]:
    rows = (
        db.query(models.Attempt, models.Quest.skill)
        .join(models.Quest, models.Quest.id == models.Attempt.quest_id)
        .filter(models.Attempt.learner_id == learner_id)
        .order_by(models.Attempt.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "quest_id": a.quest_id,
            "skill": skill,
            "correct": a.correct,
            "difficulty": a.difficulty_at_attempt,
            "points_awarded": a.points_awarded,
            "mastery_score_after": a.mastery_score_after,
            "ai_feedback": a.ai_feedback,
            "timestamp": a.timestamp.isoformat(),
        }
        for a, skill in rows
    ]


def mastery_timeline(db: Session, learner_id: str) -> list[dict]:
    """
    R5 evidence: the full chronological mastery trajectory (every attempt, in
    order), not just a single before/after snapshot - so a report can plot an
    actual mastery-over-time curve per skill instead of asserting growth
    happened. `learner_history` is capped and newest-first (an activity feed);
    this is uncapped and oldest-first (a growth curve).
    """
    rows = (
        db.query(models.Attempt, models.Quest.skill)
        .join(models.Quest, models.Quest.id == models.Attempt.quest_id)
        .filter(models.Attempt.learner_id == learner_id)
        .order_by(models.Attempt.timestamp.asc())
        .all()
    )
    return [
        {
            "skill": skill,
            "correct": a.correct,
            "mastery_score_after": a.mastery_score_after,
            "timestamp": a.timestamp.isoformat(),
        }
        for a, skill in rows
    ]
