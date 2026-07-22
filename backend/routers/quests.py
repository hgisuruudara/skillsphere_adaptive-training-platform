import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db
from backend.ethics.privacy import require_consent
from backend.ai_engine.personalization import (
    difficulty_for_mastery, fixed_progression_difficulty, DEFAULT_INITIAL_MASTERY,
)
from backend.ai_engine.scenario_generator import generate_scenario

router = APIRouter(prefix="/api/quests", tags=["quests"])


def _get_or_create_mastery(db: Session, learner_id: str, skill: str) -> models.SkillMastery:
    mastery = (
        db.query(models.SkillMastery)
        .filter(models.SkillMastery.learner_id == learner_id, models.SkillMastery.skill == skill)
        .first()
    )
    if not mastery:
        mastery = models.SkillMastery(learner_id=learner_id, skill=skill, mastery_score=DEFAULT_INITIAL_MASTERY)
        db.add(mastery)
        db.commit()
        db.refresh(mastery)
    return mastery


@router.get("", response_model=list[schemas.QuestOut])
def recommended_quests(learner_id: str, db: Session = Depends(get_db)):
    """
    Adaptive quest list: one recommended quest per module. Treatment-condition
    learners get the ZPD-based recommendation (ai_engine/personalization.py);
    control-condition learners get a fixed, non-adaptive progression - the R3
    comparative-study baseline (docs/EVALUATION_FRAMEWORK.md section 1).
    """
    learner = require_consent(db, learner_id)

    modules = db.query(models.Module).all()
    recommendations = []
    for module in modules:
        mastery = _get_or_create_mastery(db, learner_id, module.skill)
        if learner.condition == "control":
            target_difficulty = fixed_progression_difficulty(mastery.attempts_count)
        else:
            target_difficulty = difficulty_for_mastery(mastery.mastery_score)

        candidates = db.query(models.Quest).filter(models.Quest.skill == module.skill).all()
        if not candidates:
            continue
        best = min(candidates, key=lambda q: abs(q.difficulty - target_difficulty))
        recommendations.append(best)

    return recommendations


@router.post("/generate", response_model=schemas.QuestOut)
def generate_new_scenario(payload: schemas.ScenarioGenerateIn, db: Session = Depends(get_db)):
    """AI Engine 'Retrieve / Generate' path: creates a fresh scenario quest via the LLM (or fallback).
    Not available to control-condition learners, who only see seeded content
    (R3: "traditional" baseline has no AI-generated scenarios)."""
    learner = require_consent(db, payload.learner_id)
    if learner.condition == "control":
        raise HTTPException(status_code=403, detail=(
            "AI scenario generation is not available for the traditional (control) "
            "training condition - this learner is assigned to the non-AI baseline."
        ))

    module = db.query(models.Module).filter(models.Module.skill == payload.skill).first()
    if not module:
        raise HTTPException(status_code=404, detail=f"Unknown skill '{payload.skill}'")

    mastery = _get_or_create_mastery(db, payload.learner_id, payload.skill)
    difficulty = difficulty_for_mastery(mastery.mastery_score)

    generated = generate_scenario(skill=payload.skill, difficulty=difficulty, topic=payload.topic)

    quest = models.Quest(
        id=f"q_gen_{uuid.uuid4().hex[:10]}",
        module_id=module.id,
        skill=payload.skill,
        difficulty=difficulty,
        kind="scenario",
        prompt=generated["prompt"],
        options=generated["options"],
        correct_index=generated["correct_index"],
        generated_by_ai=generated["generated_by_ai"],
    )
    db.add(quest)
    db.commit()
    db.refresh(quest)
    return quest
