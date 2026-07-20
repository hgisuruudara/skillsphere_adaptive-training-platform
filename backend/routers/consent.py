from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db
from backend.ethics import privacy
from backend.analytics.engagement import log_event

router = APIRouter(prefix="/api", tags=["consent"])


@router.post("/consent", response_model=schemas.LearnerOut)
def give_consent(payload: schemas.ConsentIn, db: Session = Depends(get_db)):
    learner = db.query(models.Learner).filter(models.Learner.id == payload.learner_id).first()
    if not learner:
        learner = models.Learner(id=payload.learner_id, display_name=payload.display_name,
                                  cohort=payload.cohort)
        db.add(learner)
    else:
        learner.display_name = payload.display_name
        learner.cohort = payload.cohort

    learner.consent_given = payload.consent
    if payload.consent:
        import datetime as dt
        learner.consent_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(learner)

    privacy.record_consent(db, learner.id, payload.consent)
    if payload.consent:
        log_event(db, learner.id, "consent_given")
    return learner


@router.post("/privacy/erase")
def erase_my_data(learner_id: str, db: Session = Depends(get_db)):
    privacy.erase_learner(db, learner_id)
    return {"status": "erased", "learner_id": learner_id}
