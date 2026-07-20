import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db
from backend.ethics.privacy import require_consent
from backend.ai_engine.personalization import difficulty_for_mastery, DEFAULT_INITIAL_MASTERY
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
    Adaptive quest list: one recommended quest per module, chosen at the
    difficulty band matching the learner's current mastery in that module's
    skill (ZPD-based recommendation - see ai_engine/personalization.py).
    """
    require_consent(db, learner_id)

    modules = db.query(models.Module).all()
    recommendations = []
    for module in modules:
        mastery = _get_or_create_mastery(db, learner_id, module.skill)
        target_difficulty = difficulty_for_mastery(mastery.mastery_score)

        candidates = db.query(models.Quest).filter(models.Quest.skill == module.skill).all()
        if not candidates:
            continue
        best = min(candidates, key=lambda q: abs(q.difficulty - target_difficulty))
        recommendations.append(best)

    return recommendations


@router.post("/generate", response_model=schemas.QuestOut)
def generate_new_scenario(payload: schemas.ScenarioGenerateIn, db: Session = Depends(get_db)):
    """AI Engine 'Retrieve / Generate' path: creates a fresh scenario quest via the LLM (or fallback)."""
    require_consent(db, payload.learner_id)

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
