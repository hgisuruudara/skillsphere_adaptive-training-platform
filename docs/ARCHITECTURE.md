# System Architecture

This document describes the architecture of the SkillSphere prototype and
shows how it implements the conceptual architecture diagram from the thesis
proposal. Every box in the original diagram corresponds to a real,
runnable module in this repository - nothing here is purely conceptual.

## 1. High-level component diagram

```mermaid
flowchart LR
    Learner["Corporate Learner\n(Web / Mobile Interface)"]

    subgraph UI["Gamified Training Interface"]
        direction TB
        UIcomp["Quests · Levels · Points & Badges\nfrontend/index.html + js/app.js"]
    end

    subgraph GE["Gamification Engine"]
        direction TB
        GEcomp["Rules · Progression · Rewards\nbackend/gamification/engine.py"]
    end

    subgraph AI["LLM-Based AI Engine"]
        direction TB
        AIcomp["Personalization · Adaptive Feedback · Scenario Generation\nbackend/ai_engine/*"]
    end

    subgraph ANA["Learning Analytics Module"]
        direction TB
        ANAcomp["Engagement Metrics · Performance Logs\nbackend/analytics/*"]
    end

    subgraph EPL["Ethics & Privacy Layer"]
        direction TB
        EPLcomp["Consent · Bias Mitigation · Data Governance\nbackend/ethics/*"]
    end

    subgraph TCR["Training Content Repository"]
        direction TB
        TCRcomp["Modules · Scenarios · Assessments\nmodels.Module / models.Quest"]
    end

    subgraph LPS["Learner Profile Store"]
        direction TB
        LPScomp["Skills · Preferences · History\nmodels.Learner / models.SkillMastery"]
    end

    Dash["Instructor / Admin Dashboard\nfrontend/dashboard.html"]

    Learner -- "Interaction" --> UI
    UI -- "Gameplay Events\n(attempts, response time)" --> GE
    GE -- "Learner Context" --> AI
    AI -- "Adaptive Decisions\n(next difficulty, feedback)" --> GE
    GE -- "Scores & Engagement" --> ANA
    EPL -- "Ethical Constraints" --> AI
    EPL -- "Compliance Rules" --> ANA
    AI -- "Retrieve / Generate" --> TCR
    AI -- "Read / Update" --> LPS
    ANA -- "Reports & Insights" --> Dash
```

This is a direct implementation of the thesis's conceptual diagram; the only
addition is explicit source-file references so the diagram is traceable to
code, which matters when this document is used as thesis evidence.

## 2. Request/response sequence for one gameplay loop

The single most important flow in the system - a learner answering a
question and the AI/gamification engines reacting - is implemented in
`backend/routers/gameplay.py::submit_attempt`. Sequence:

```mermaid
sequenceDiagram
    participant L as Learner (browser)
    participant API as FastAPI (gameplay.py)
    participant Ethics as Ethics Layer (privacy.py)
    participant AI as AI Engine (personalization.py)
    participant Game as Gamification Engine (engine.py)
    participant LLM as LLM Client (llm_client.py)
    participant DB as SQLite (models.py)

    L->>API: POST /api/attempts {quest_id, selected_index, response_time_ms}
    API->>Ethics: require_consent(learner_id)
    Ethics-->>API: 403 if no consent, else learner record
    API->>DB: fetch Quest, SkillMastery
    API->>AI: update_mastery(current_mastery, correct)
    AI-->>API: new_mastery, new_streak, recommended_difficulty
    API->>Game: score_attempt(points, level, badges)
    Game-->>API: points_awarded, new_level, level_up
    API->>LLM: chat_complete(feedback prompt) [or offline fallback]
    LLM-->>API: personalized feedback text
    API->>DB: persist Attempt, Badge rows, updated Learner/SkillMastery
    API->>DB: log_event("quest_complete")  [Learning Analytics Module]
    API-->>L: {correct, points, level_up, new_badges, ai_feedback, next_recommended_difficulty}
```

Note that the AI Engine and Gamification Engine are **pure, independently
testable functions** (see `tests/test_ai_engine.py`,
`tests/test_gamification.py`) - the router only orchestrates side effects
(DB writes, HTTP). This separation is what makes the adaptive logic
auditable, which matters for the ethics/fairness objective (R4): an
instructor or auditor can reason about `update_mastery()` and
`difficulty_for_mastery()` without needing to trace HTTP plumbing.

## 3. Data model (Entity-Relationship)

```mermaid
erDiagram
    LEARNER ||--o{ SKILL_MASTERY : has
    LEARNER ||--o{ ATTEMPT : makes
    LEARNER ||--o{ BADGE : earns
    LEARNER ||--o{ CONSENT_RECORD : records
    LEARNER ||--o{ ENGAGEMENT_EVENT : generates
    MODULE ||--o{ QUEST : contains
    QUEST ||--o{ ATTEMPT : "attempted via"

    LEARNER {
        string id PK
        string display_name
        string cohort
        int total_points
        int level
        bool consent_given
        datetime erased_at
    }
    SKILL_MASTERY {
        string learner_id FK
        string skill
        float mastery_score
        int attempts_count
        int correct_streak
    }
    MODULE {
        string id PK
        string title
        string skill
    }
    QUEST {
        string id PK
        string module_id FK
        int difficulty
        string kind
        json options
        int correct_index
        bool generated_by_ai
    }
    ATTEMPT {
        string learner_id FK
        string quest_id FK
        bool correct
        int points_awarded
        text ai_feedback
    }
    BADGE {
        string learner_id FK
        string code
        string name
    }
    CONSENT_RECORD {
        string learner_id FK
        bool consent
        string policy_version
    }
    ENGAGEMENT_EVENT {
        string learner_id FK
        string event_type
        json meta
    }
```

## 4. Component responsibilities

| Diagram box | Module(s) | Responsibility |
|---|---|---|
| Gamified Training Interface | `frontend/index.html`, `frontend/js/app.js` | Renders quests, points, level, badges; captures gameplay events (answer + response time) |
| Gamification Engine | `backend/gamification/engine.py` | Deterministic scoring, level curve, badge rules, quest progression |
| LLM-Based AI Engine | `backend/ai_engine/personalization.py`, `llm_client.py`, `scenario_generator.py` | Mastery estimation (EMA), ZPD-based difficulty recommendation, adaptive feedback generation, scenario generation |
| Ethics & Privacy Layer | `backend/ethics/privacy.py`, `bias_mitigation.py` | Consent gating, right-to-erasure, cohort fairness auditing |
| Learning Analytics Module | `backend/analytics/engagement.py`, `reporting.py` | Event logging, engagement/performance/fairness aggregation |
| Training Content Repository | `backend/models.py::Module/Quest`, `seed_data.py` | Pre-authored + AI-generated modules, scenarios, assessments |
| Learner Profile Store | `backend/models.py::Learner/SkillMastery` | Skills (mastery per skill), preferences, history |
| Instructor/Admin Dashboard | `frontend/dashboard.html`, `js/dashboard.js` | Engagement charts, fairness monitor, leaderboard |

## 5. Why FastAPI + SQLite + vanilla JS (design rationale)

- **FastAPI**: async-first, Pydantic-validated request/response schemas give
  the API a typed contract (`backend/schemas.py`) that doubles as
  machine-readable documentation (`/docs`) - useful when the prototype is
  handed to research assistants running a pilot study who are not the
  original developer.
- **SQLite**: zero-ops relational storage appropriate for a pilot-scale
  study (tens to low hundreds of learners); the SQLAlchemy layer means
  migrating to Postgres later is a one-line `DATABASE_URL` change, not a
  rewrite.
- **Vanilla JS**: no build step, no framework version drift, runs by
  opening two HTML files served as static assets - minimizes the technical
  barrier for a non-engineering thesis committee to run the demo themselves.
- **Anthropic Claude API with offline fallback**: keeps the "AI" in "AI-driven
  gamification" real (the architecture genuinely calls an LLM), while making
  the prototype's core adaptive behaviour reproducible without network
  access or API cost, which is essential for a controlled comparative study
  (R3) and for grading/demoing without exposing API keys.
