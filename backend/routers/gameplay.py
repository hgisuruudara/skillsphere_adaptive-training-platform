import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db
from backend.ethics.privacy import require_consent
from backend.gamification.engine import score_attempt, evaluate_badges
from backend.ai_engine.personalization import (
    update_mastery, build_feedback_prompt, fallback_feedback, fixed_progression_difficulty,
)
from backend.ai_engine.mastery_models import bkt_update
from backend.ai_engine.llm_client import chat_complete
from backend.analytics.engagement import log_event
from backend.routers.quests import _get_or_create_mastery

router = APIRouter(prefix="/api", tags=["gameplay"])


@router.post("/attempts", response_model=schemas.AttemptResultOut)
def submit_attempt(payload: schemas.AttemptIn, db: Session = Depends(get_db)):
    learner = require_consent(db, payload.learner_id)

    quest = db.query(models.Quest).filter(models.Quest.id == payload.quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    correct = payload.selected_index == quest.correct_index
    mastery = _get_or_create_mastery(db, learner.id, quest.skill)

    # --- AI Engine: adaptivity (R1) ---
    # Primary estimator (EMA) drives the real difficulty decision below.
    update = update_mastery(current_mastery=mastery.mastery_score,
                             current_streak=mastery.correct_streak, correct=correct)
    mastery.mastery_score = update.new_mastery
    mastery.correct_streak = update.new_streak
    mastery.attempts_count += 1

    # Shadow estimator (BKT) computed in parallel on the same evidence, purely
    # for R1 technique comparison (see ai_engine/mastery_models.py) - it does
    # not influence difficulty or scoring.
    bkt_result = bkt_update(prior_mastery=mastery.mastery_score_bkt, correct=correct)
    mastery.mastery_score_bkt = bkt_result.new_mastery

    # --- Gamification Engine: scoring & progression ---
    scoring = score_attempt(
        total_points_before=learner.total_points,
        difficulty=quest.difficulty,
        correct=correct,
        response_time_ms=payload.response_time_ms,
        correct_streak_after=update.new_streak,
    )
    learner.total_points = scoring.new_total_points
    learner.level = scoring.new_level

    existing_badge_codes = {b.code for b in db.query(models.Badge).filter(models.Badge.learner_id == learner.id).all()}
    distinct_days = {
        e.timestamp.date() for e in db.query(models.EngagementEvent)
        .filter(models.EngagementEvent.learner_id == learner.id).all()
    }
    newly_earned = evaluate_badges(
        existing_badge_codes,
        is_first_attempt=mastery.attempts_count == 1,
        correct_streak=update.new_streak,
        mastery_score=update.new_mastery,
        distinct_days_active=len(distinct_days) + 1,
    )
    for code, name in newly_earned:
        db.add(models.Badge(learner_id=learner.id, code=code, name=name))

    # --- AI Engine: adaptive feedback generation (R1) ---
    # R3: control-condition learners get only a static templated message (the
    # "traditional gamified training" baseline) - no LLM call, no past-mistake
    # lookup, no personalization. Treatment-condition learners get the full
    # adaptive feedback pipeline. Mastery/BKT are still tracked for BOTH
    # conditions above, so growth rates remain comparable between groups.
    if learner.condition == "control":
        feedback_text = "Correct." if correct else "Incorrect."
        next_recommended_difficulty = fixed_progression_difficulty(mastery.attempts_count)
    else:
        # Look up the learner's most recent *incorrect* attempt on this same
        # skill (queried before today's attempt is added, so it naturally
        # excludes it) so feedback can reference a specific past error, not
        # just a difficulty number - a second, independent personalization
        # dimension.
        previous_mistake_row = (
            db.query(models.Quest.prompt)
            .join(models.Attempt, models.Attempt.quest_id == models.Quest.id)
            .filter(models.Attempt.learner_id == learner.id, models.Quest.skill == quest.skill,
                    models.Attempt.correct.is_(False))
            .order_by(models.Attempt.timestamp.desc())
            .first()
        )
        previous_mistake = previous_mistake_row[0] if previous_mistake_row else None

        system_prompt, user_prompt = build_feedback_prompt(
            learner_display_name=learner.display_name, skill=quest.skill, correct=correct,
            mastery_score=update.new_mastery, difficulty=quest.difficulty, prompt_text=quest.prompt,
            previous_mistake=previous_mistake,
        )
        fallback_text = fallback_feedback(correct=correct, skill=quest.skill,
                                           mastery_score=update.new_mastery, difficulty=quest.difficulty,
                                           previous_mistake=previous_mistake)
        feedback_result = chat_complete(system_prompt, user_prompt, fallback_text=fallback_text)
        feedback_text = feedback_result.text
        next_recommended_difficulty = update.recommended_difficulty

    attempt = models.Attempt(
        learner_id=learner.id, quest_id=quest.id, correct=correct,
        difficulty_at_attempt=quest.difficulty, response_time_ms=payload.response_time_ms,
        points_awarded=scoring.points_awarded, ai_feedback=feedback_text,
        timestamp=dt.datetime.utcnow(),
    )
    db.add(attempt)
    db.commit()

    log_event(db, learner.id, "quest_complete", {"quest_id": quest.id, "correct": correct})

    return schemas.AttemptResultOut(
        correct=correct,
        points_awarded=scoring.points_awarded,
        total_points=scoring.new_total_points,
        level=scoring.new_level,
        level_up=scoring.level_up,
        new_badges=[name for _, name in newly_earned],
        mastery_score=update.new_mastery,
        next_recommended_difficulty=next_recommended_difficulty,
        ai_feedback=feedback_text,
    )
