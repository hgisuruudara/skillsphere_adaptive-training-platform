from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db
from backend.analytics.reporting import learner_history, mastery_timeline

router = APIRouter(prefix="/api/learners", tags=["learners"])


@router.get("/{learner_id}/profile", response_model=schemas.LearnerProfileOut)
def get_profile(learner_id: str, db: Session = Depends(get_db)):
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    skills = db.query(models.SkillMastery).filter(models.SkillMastery.learner_id == learner_id).all()
    badges = db.query(models.Badge).filter(models.Badge.learner_id == learner_id).all()
    history = learner_history(db, learner_id)
    timeline = mastery_timeline(db, learner_id)

    return schemas.LearnerProfileOut(
        learner=learner,
        skills=skills,
        badges=badges,
        recent_history=history,
        mastery_timeline=timeline,
    )
