import datetime as dt

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
)
from sqlalchemy.orm import relationship

from backend.database import Base


def utcnow():
    return dt.datetime.utcnow()


class Learner(Base):
    """Learner Profile Store: identity, preferences, consent state."""
    __tablename__ = "learners"

    id = Column(String, primary_key=True)  # slug/handle chosen at signup
    display_name = Column(String, nullable=False)
    cohort = Column(String, nullable=True)  # non-sensitive grouping (e.g. team/dept) for fairness monitoring
    condition = Column(String, default="treatment")  # "treatment" (AI-driven) | "control" (traditional) - R3 comparative study
    preferences = Column(JSON, default=dict)  # e.g. {"learning_style": "visual"}
    total_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)

    consent_given = Column(Boolean, default=False)
    consent_at = Column(DateTime, nullable=True)
    erased_at = Column(DateTime, nullable=True)  # set on right-to-erasure

    skills = relationship("SkillMastery", back_populates="learner", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="learner", cascade="all, delete-orphan")
    badges = relationship("Badge", back_populates="learner", cascade="all, delete-orphan")


class SkillMastery(Base):
    """Per-skill mastery estimate feeding the AI Engine's adaptivity decisions."""
    __tablename__ = "skill_mastery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False)
    skill = Column(String, nullable=False)
    mastery_score = Column(Float, default=0.3)  # 0..1, EMA-updated - drives real difficulty decisions
    mastery_score_bkt = Column(Float, default=0.3)  # 0..1, Bayesian Knowledge Tracing - shadow metric for R1 technique comparison, does not affect gameplay
    attempts_count = Column(Integer, default=0)
    correct_streak = Column(Integer, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    learner = relationship("Learner", back_populates="skills")


class Module(Base):
    """Training Content Repository: top-level module grouping."""
    __tablename__ = "modules"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    skill = Column(String, nullable=False)


class Quest(Base):
    """Training Content Repository: an individual quest/scenario/assessment item."""
    __tablename__ = "quests"

    id = Column(String, primary_key=True)
    module_id = Column(String, ForeignKey("modules.id"), nullable=False)
    skill = Column(String, nullable=False)
    difficulty = Column(Integer, default=1)  # 1 (easy) .. 5 (hard)
    kind = Column(String, default="quiz")  # quiz | scenario
    prompt = Column(Text, nullable=False)
    options = Column(JSON, default=list)  # list[str]
    correct_index = Column(Integer, nullable=False)
    generated_by_ai = Column(Boolean, default=False)


class Attempt(Base):
    """Performance log: one learner's attempt at one quest."""
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False)
    quest_id = Column(String, ForeignKey("quests.id"), nullable=False)
    correct = Column(Boolean, nullable=False)
    difficulty_at_attempt = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, default=0)
    points_awarded = Column(Integer, default=0)
    ai_feedback = Column(Text, default="")
    timestamp = Column(DateTime, default=utcnow)

    learner = relationship("Learner", back_populates="attempts")


class Badge(Base):
    """Gamification Engine reward record."""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    awarded_at = Column(DateTime, default=utcnow)

    learner = relationship("Learner", back_populates="badges")


class EngagementEvent(Base):
    """Learning Analytics Module: raw engagement/telemetry events."""
    __tablename__ = "engagement_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False)
    event_type = Column(String, nullable=False)  # e.g. login, quest_start, quest_complete
    meta = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=utcnow)


class ConsentRecord(Base):
    """Ethics & Privacy Layer: immutable audit trail of consent decisions."""
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False)
    consent = Column(Boolean, nullable=False)
    policy_version = Column(String, default="1.0")
    timestamp = Column(DateTime, default=utcnow)
