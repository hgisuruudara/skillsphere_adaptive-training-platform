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
from statistics import mean

from sqlalchemy.orm import Session

from backend import models
from backend.ethics.bias_mitigation import audit_cohort_fairness


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


def learner_history(db: Session, learner_id: str, limit: int = 20) -> list[dict]:
    attempts = (
        db.query(models.Attempt)
        .filter(models.Attempt.learner_id == learner_id)
        .order_by(models.Attempt.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "quest_id": a.quest_id,
            "correct": a.correct,
            "difficulty": a.difficulty_at_attempt,
            "points_awarded": a.points_awarded,
            "ai_feedback": a.ai_feedback,
            "timestamp": a.timestamp.isoformat(),
        }
        for a in attempts
    ]
