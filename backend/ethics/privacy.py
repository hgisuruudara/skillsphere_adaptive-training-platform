"""
Privacy & Consent (Ethics & Privacy Layer -> "Compliance Rules" / "Ethical Constraints")
=========================================================================================
Addresses Research Question 4 (R4): consent management and data governance
(right to erasure) for a system that collects detailed behavioural data.

Design principles applied:
  - Consent is explicit, versioned, and recorded as an immutable audit trail
    (ConsentRecord rows are never edited, only appended).
  - No gameplay/analytics data is written for a learner until consent==True
    (enforced by `require_consent`, called from the gameplay router).
  - Right to erasure: `erase_learner` anonymizes identifying fields while
    preserving aggregate statistics needed for the Learning Analytics Module,
    following a data-minimization / pseudonymization approach rather than a
    hard delete that would corrupt historical cohort reporting.
"""
import datetime as dt

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models


class ConsentRequiredError(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail=(
            "Consent has not been granted for this learner. No training data "
            "can be collected or processed until explicit consent is recorded."
        ))


def require_consent(db: Session, learner_id: str) -> models.Learner:
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner or not learner.consent_given or learner.erased_at:
        raise ConsentRequiredError()
    return learner


def record_consent(db: Session, learner_id: str, consent: bool, policy_version: str = "1.0") -> None:
    record = models.ConsentRecord(learner_id=learner_id, consent=consent, policy_version=policy_version)
    db.add(record)
    db.commit()


def erase_learner(db: Session, learner_id: str) -> None:
    """
    Right-to-erasure: scrub direct identifiers, keep anonymized skill/attempt
    aggregates intact for organizational analytics (a defensible middle ground
    between full deletion and unrestricted retention).
    """
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner:
        return
    learner.display_name = "erased-learner"
    learner.cohort = None
    learner.preferences = {}
    learner.erased_at = dt.datetime.utcnow()
    db.commit()
