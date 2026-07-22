import datetime as dt
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ConsentIn(BaseModel):
    learner_id: str
    display_name: str
    cohort: Optional[str] = None
    consent: bool


class LearnerOut(BaseModel):
    id: str
    display_name: str
    cohort: Optional[str]
    condition: str
    total_points: int
    level: int
    consent_given: bool

    class Config:
        from_attributes = True


class SkillMasteryOut(BaseModel):
    skill: str
    mastery_score: float
    mastery_score_bkt: float
    attempts_count: int
    correct_streak: int

    class Config:
        from_attributes = True


class BadgeOut(BaseModel):
    code: str
    name: str
    awarded_at: dt.datetime

    class Config:
        from_attributes = True


class QuestOut(BaseModel):
    id: str
    module_id: str
    skill: str
    difficulty: int
    kind: str
    prompt: str
    options: List[str]
    generated_by_ai: bool

    class Config:
        from_attributes = True


class LearnerProfileOut(BaseModel):
    learner: LearnerOut
    skills: List[SkillMasteryOut]
    badges: List[BadgeOut]
    recent_history: List[Dict[str, Any]]


class AttemptIn(BaseModel):
    learner_id: str
    quest_id: str
    selected_index: int
    response_time_ms: int = Field(ge=0, default=0)


class AttemptResultOut(BaseModel):
    correct: bool
    points_awarded: int
    total_points: int
    level: int
    level_up: bool
    new_badges: List[str]
    mastery_score: float
    next_recommended_difficulty: int
    ai_feedback: str


class ScenarioGenerateIn(BaseModel):
    learner_id: str
    skill: str
    topic: Optional[str] = None


class DashboardMetricsOut(BaseModel):
    total_learners: int
    consented_learners: int
    total_attempts: int
    overall_accuracy: float
    avg_response_time_ms: float
    active_last_7_days: int
    engagement_by_day: List[Dict[str, Any]]
    fairness_monitor: List[Dict[str, Any]]
    top_learners: List[Dict[str, Any]]
    technique_comparison: Dict[str, Any]


class ComparisonStatsOut(BaseModel):
    control: Dict[str, Any]
    treatment: Dict[str, Any]
    cohens_d: Optional[float]
    effect_size_interpretation: Optional[str]
    note: str
