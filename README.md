# SkillSphere - AI-Driven Adaptive Gamified Training Platform

**A working micro-prototype built as empirical evidence for the thesis:**
*"Exploring the Integration of Artificial Intelligence in Gamification and
Serious Games for Corporate Training."*

SkillSphere is a runnable, end-to-end demonstration of every component in the
proposed system architecture: a gamified training interface, a rules-based
gamification engine, an LLM-based AI engine for personalization/adaptivity,
an ethics & privacy layer, a learning analytics module, and an instructor
dashboard. It is deliberately small enough to read end-to-end in an
afternoon, while being complete enough to run a real pilot study against.

## Why this exists

A thesis about AI-enhanced gamified corporate training needs more than a
literature review - it needs a concrete artifact that operationalizes the
research questions (R1-R5) so they can be tested empirically (comparative
study, ethics review, evaluation metrics). This repository *is* that
artifact. See [`docs/THESIS_MAPPING.md`](docs/THESIS_MAPPING.md) for exactly
how each piece of code maps back to an objective or research question.

## Documentation map

| Document | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, component diagrams, data flow (matches the thesis architecture diagram) |
| [`docs/TECHNICAL_BACKGROUND.md`](docs/TECHNICAL_BACKGROUND.md) | Theoretical foundations: gamification frameworks, SDT, Flow, ZPD, AI personalization techniques, LLM background |
| [`docs/DEVELOPMENT_GUIDE.md`](docs/DEVELOPMENT_GUIDE.md) | Step-by-step guide to building this system from an empty repository |
| [`docs/ETHICS_PRIVACY.md`](docs/ETHICS_PRIVACY.md) | Consent, data governance, bias mitigation design (R4) |
| [`docs/EVALUATION_FRAMEWORK.md`](docs/EVALUATION_FRAMEWORK.md) | Comparative study design (R3) and evaluation metrics/methods (R5) |
| [`docs/THESIS_MAPPING.md`](docs/THESIS_MAPPING.md) | Traceability matrix: research objectives/questions -> code -> evidence |

## Tech stack

| Layer | Technology | Where |
|---|---|---|
| Frontend | HTML + CSS + vanilla JavaScript | `frontend/` |
| Backend / API | Python + FastAPI | `backend/` |
| LLM | Anthropic Claude API (`claude-opus-4-8`), with a fully offline deterministic fallback | `backend/ai_engine/` |
| Data storage | SQLite (via SQLAlchemy ORM) | `backend/models.py`, `skillsphere.db` |
| Tests | pytest + FastAPI TestClient | `tests/` |
| Deployment | Uvicorn (localhost or any PaaS, e.g. Render) | `run.py` |

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # optional: add ANTHROPIC_API_KEY for live LLM calls
python run.py                     # starts on http://localhost:8000
```

Then open:
- `http://localhost:8000/` - the learner-facing gamified training interface
- `http://localhost:8000/dashboard` - the instructor/admin analytics dashboard
- `http://localhost:8000/docs` - auto-generated OpenAPI/Swagger docs for every endpoint

Run the test suite:

```bash
python -m pytest -q
```

**No Anthropic API key is required.** If `ANTHROPIC_API_KEY` is unset, the AI
Engine automatically runs in a deterministic "fallback mode" (see
`backend/ai_engine/llm_client.py`) so the whole prototype - adaptive
difficulty, personalized feedback, scenario generation - still functions
fully offline and reproducibly, which matters for grading and for running
controlled comparative studies (R3).

## Repository layout

```
backend/
  models.py, schemas.py, database.py   # data layer (Learner Profile Store, Content Repository)
  gamification/engine.py               # Gamification Engine (points, levels, badges)
  ai_engine/                           # LLM-Based AI Engine (personalization, adaptive feedback, scenario generation)
  ethics/                              # Ethics & Privacy Layer (consent, bias mitigation)
  analytics/                           # Learning Analytics Module (engagement, reporting)
  routers/                             # FastAPI route handlers wiring it all together
  main.py                              # app entrypoint
frontend/
  index.html, dashboard.html, css/, js/
tests/
docs/
```

For a full guided walkthrough of *why* the system is structured this way and
*how* to rebuild it from scratch, start with
[`docs/DEVELOPMENT_GUIDE.md`](docs/DEVELOPMENT_GUIDE.md).
