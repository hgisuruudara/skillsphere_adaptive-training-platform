"""
Engagement Logging
==================
Writes the raw telemetry events that the Learning Analytics Module later
aggregates. Kept deliberately dumb (append-only) so the event log itself is
never a bottleneck or a place where business logic sneaks in.
"""
from sqlalchemy.orm import Session

from backend import models


def log_event(db: Session, learner_id: str, event_type: str, meta: dict | None = None) -> None:
    event = models.EngagementEvent(learner_id=learner_id, event_type=event_type, meta=meta or {})
    db.add(event)
    db.commit()
