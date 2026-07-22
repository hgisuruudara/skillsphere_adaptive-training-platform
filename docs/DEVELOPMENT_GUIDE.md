# Development Guide: Building SkillSphere From Scratch

This guide walks through building this exact system from an empty
repository, in the order it was actually built. It is written so it can be
used as thesis appendix material ("Methodology - System Implementation") or
followed literally to reproduce/extend the prototype.

## 0. Prerequisites

- Python 3.10+
- (Optional) an Anthropic API key, only needed for live LLM calls
- No database server, no Node.js, no build tooling required

## 1. Decide the architecture before writing code

Start from the conceptual architecture diagram (Learner → Gamified
Interface → Gamification Engine ↔ AI Engine → Content Repository / Learner
Profile Store, with an Ethics & Privacy Layer feeding constraints, and a
Learning Analytics Module feeding the Instructor Dashboard). Translate every
box into a concrete module *before* writing implementation code:

| Diagram box | Planned module |
|---|---|
| Gamified Training Interface | `frontend/` |
| Gamification Engine | `backend/gamification/` |
| LLM-Based AI Engine | `backend/ai_engine/` |
| Ethics & Privacy Layer | `backend/ethics/` |
| Learning Analytics Module | `backend/analytics/` |
| Training Content Repository | `backend/models.py` (`Module`, `Quest`) + `backend/seed_data.py` |
| Learner Profile Store | `backend/models.py` (`Learner`, `SkillMastery`) |
| Instructor/Admin Dashboard | `frontend/dashboard.html` |

This 1:1 mapping is what makes the finished repo directly defensible as
"the architecture, implemented" rather than a loosely-related demo.

## 2. Scaffold the project

```
mkdir -p backend/{gamification,ai_engine,ethics,analytics,routers}
mkdir -p frontend/{css,js}
mkdir -p tests docs
```

Pin dependencies in `requirements.txt` (FastAPI, Uvicorn, SQLAlchemy,
Pydantic, python-dotenv, anthropic, pytest, httpx). Add `.env.example` and
`.gitignore` (excluding `.env`, `*.db`, `__pycache__/`).

## 3. Build the data layer first

Data model design should happen before any endpoint code, because it forces
you to decide what "adaptivity," "engagement," and "consent" concretely mean
as stored fields.

1. `backend/config.py` - centralizes environment configuration
   (`DATABASE_URL`, `ANTHROPIC_API_KEY`) behind a single `settings` object, and
   exposes `settings.llm_enabled` so the rest of the app never checks env
   vars directly.
2. `backend/database.py` - SQLAlchemy engine/session/`Base`, plus
   `init_db()` called once at startup.
3. `backend/models.py` - one ORM class per architecture box's data need:
   `Learner`, `SkillMastery`, `Module`, `Quest`, `Attempt`, `Badge`,
   `EngagementEvent`, `ConsentRecord`. Add a one-line docstring to each class
   naming which architecture box it belongs to - this is what keeps the
   traceability matrix in `docs/THESIS_MAPPING.md` honest.
4. `backend/schemas.py` - Pydantic request/response models. Keep these
   separate from ORM models so the API contract can evolve independently of
   storage.

**Checkpoint:** you should be able to `python -c "from backend.database import
init_db; init_db()"` and see `skillsphere.db` created with all tables, before
writing a single endpoint.

**No migration tooling by design:** `init_db()` only creates tables that don't
exist yet (`Base.metadata.create_all()`); it never alters an existing table.
So after pulling code with a model change (a new column, a new table), an
old `skillsphere.db` will throw `sqlite3.OperationalError: no such column: ...`
- the fix is to delete `skillsphere.db` and restart the app, which recreates
it from the current models and reseeds content automatically. **Always stop
the running server first.** Deleting the file out from under a server that
still has it open doesn't just lose data - a new connection opened afterward
can create a fresh, empty file at that path while the old process's
connections are still confused about what they're pointing at, which is what
produces the harder-to-diagnose `attempt to write a readonly database` error
rather than a clean recreate.

## 4. Build each engine as a pure, framework-free module

This is the most important discipline in the whole guide: **build the
Gamification Engine and AI Engine as plain Python functions with no FastAPI
or SQLAlchemy imports.** This is what let this project have a full unit
test suite (`tests/test_gamification.py`, `tests/test_ai_engine.py`) before
a single HTTP route existed.

1. `backend/gamification/engine.py`:
   - `compute_points(difficulty, correct, response_time_ms, correct_streak)`
   - `level_for_points(total_points)`
   - `evaluate_badges(...)`
   - `score_attempt(...)` composing the above
2. `backend/ai_engine/personalization.py`:
   - `update_mastery(current_mastery, current_streak, correct)` - the EMA
     adaptivity model
   - `difficulty_for_mastery(mastery)` - the ZPD-based recommender
   - `build_feedback_prompt(...)` / `fallback_feedback(...)` - LLM prompt
     construction with a non-LLM fallback string
3. `backend/ai_engine/llm_client.py`:
   - a single `chat_complete(system_prompt, user_prompt, fallback_text)`
     function that tries the Anthropic Claude API and *always* degrades to
     `fallback_text` on any exception or missing key. This one function is
     what makes the entire system runnable offline.
4. `backend/ai_engine/scenario_generator.py`:
   - `generate_scenario(skill, difficulty, topic)` calling `chat_complete`
     with a JSON-only system prompt, parsing the result, and falling back to
     a small hand-authored template bank per skill if parsing fails or the
     LLM is unavailable.
5. `backend/ethics/privacy.py` and `bias_mitigation.py`:
   - `require_consent(db, learner_id)` raising `403` if consent is missing
     or the learner record has been erased
   - `record_consent`, `erase_learner` (pseudonymize-not-delete)
   - `audit_cohort_fairness(rows)` - pure statistics function comparing
     per-cohort averages against the overall average

Write unit tests for each of these **before** wiring up routes. If a rule
("badges shouldn't be re-awarded", "mastery must stay in [0,1]", "no points
for wrong answers") can be tested without a running server, test it that
way first.

## 5. Build the analytics layer

`backend/analytics/engagement.py::log_event` is an intentionally dumb
append-only writer. `backend/analytics/reporting.py::build_dashboard_metrics`
does all the aggregation: engagement-by-day, overall accuracy, fairness
monitor (delegating to `ethics/bias_mitigation.py`), leaderboard. Keeping
aggregation in one function makes it trivial to unit test against a
hand-built list of fake rows without touching the DB (extend
`tests/test_ethics.py`'s pattern here if you add more metrics).

## 6. Wire it all together with FastAPI routers

Only now do routers get written, and they should contain **almost no
logic** - just: validate input → call ethics gate → call engine functions →
persist → return. Compare `backend/routers/gameplay.py::submit_attempt`:
it calls `require_consent`, `update_mastery`, `score_attempt`,
`evaluate_badges`, `chat_complete`, and `log_event` - all functions built and
tested in steps 3-5 - and does nothing itself except sequence them and
commit the DB session.

Router order to build:
1. `routers/consent.py` - nothing else can be tested end-to-end without this
2. `routers/learners.py` - profile read endpoint
3. `routers/quests.py` - adaptive recommendation + AI generation
4. `routers/gameplay.py` - the core attempt-submission loop
5. `routers/dashboard.py` - metrics read endpoint

## 7. Seed realistic content

`backend/seed_data.py` defines 4 modules × 4 quests spanning difficulty 1-4,
covering four corporate-training verticals (workplace safety, customer
service, data privacy, new-employee onboarding compliance) so the demo is
domain-realistic rather than abstract "Question 1, Question 2"
placeholders - the fourth vertical was added later specifically to
demonstrate the framework generalizes to a new domain with zero engine
changes (R2). `seed()` checks each row's ID individually rather than an
all-or-nothing `count() == 0`, so it stays idempotent even as new content is
added to an existing database.

## 8. Assemble `main.py`

- `lifespan` context manager calls `init_db()` then `seed_data.seed()` once
  at startup.
- Include all five routers.
- Mount `frontend/` as static files, and serve `index.html` /
  `dashboard.html` at `/` and `/dashboard` respectively, so the whole app is
  a single process with no separate frontend server or CORS complexity in
  production (CORS middleware is still added permissively for local API
  testing with tools like `curl`/Postman).

## 9. Build the frontend against the already-working API

Because the API was fully testable via `curl`/pytest before any HTML
existed, the frontend build is just: render `fetch()` responses into DOM.
`frontend/js/app.js` implements: consent form → profile/quest fetch →
answer submission → feedback rendering, all against endpoints that already
had passing tests. `frontend/js/dashboard.js` polls
`/api/dashboard/metrics` every 15s and renders stat tiles, a CSS bar chart,
the fairness table, and the leaderboard.

## 10. Test end-to-end, not just unit-by-unit

Add `tests/test_api.py` using FastAPI's `TestClient` against a temporary
SQLite file. `tests/conftest.py` sets `DATABASE_URL` to a fresh temp path
before any test module can import `backend.database`/`backend.models` (it
runs first, as pytest's own convention guarantees), so every test file gets
an isolated DB from a plain import - no `importlib.reload()` gymnastics
needed. Assert the full loop: consent gate returns 403 before consent,
quests appear after consent, an attempt updates mastery/points/badges, AI
generation returns a valid quest shape, dashboard metrics reflect the new
data, and erasure anonymizes the profile.

Then manually smoke-test with the real server running (`python run.py`) and
`curl`, checking the exact same sequence a learner's browser would perform.
This step caught, in the original build of this prototype, that the
`/api/quests` recommender creates a `SkillMastery` row for *every* module
(not just the one the learner is about to attempt) - correct behaviour, but
worth verifying against a running instance rather than assuming from the
code.

## 11. Document last, but immediately

Write the architecture/background/ethics/evaluation docs while the design
decisions are still fresh, cross-referencing exact file paths and function
names (as this guide does) so the documentation cannot silently drift out
of sync with the code it describes.

## 12. Deploying

For a pilot study, the simplest path is a single-dyno deployment (e.g.
Render, Railway, Fly.io): point the service at `uvicorn backend.main:app`,
set `DATABASE_URL` to a persistent-disk SQLite path (or a managed
Postgres URL if scaling beyond a pilot), and set `ANTHROPIC_API_KEY` as a
secret environment variable if live generation is desired. No other
infrastructure (queues, caches, CDNs) is required at pilot scale.

## 13. Later additions (evidence-focused, not a rebuild)

Steps 1-12 describe the original build. A second pass then strengthened the
research-question evidence without changing the architecture:

- **R1**: `backend/ai_engine/mastery_models.py` (`bkt_update`) added a second
  mastery estimator computed alongside the original EMA one, purely for
  comparison (`analytics/reporting.py::_technique_comparison`); adaptive
  feedback was extended to reference a learner's specific past mistake.
- **R2**: a fourth training vertical (onboarding compliance) was added to
  `seed_data.py` to demonstrate the framework generalizes.
- **R3**: `Learner.condition` plus branching in `routers/quests.py` and
  `routers/gameplay.py` turned the previously-*proposed* comparative study
  design into a runnable one, with `comparative_study_stats()` computing a
  Cohen's d effect size.
- **R4**: `bias_mitigation.py`'s fairness flag was upgraded to require a
  Welch's t-test (implemented from scratch, no new dependency) in addition
  to the original fixed-threshold check, and `scripts/synthetic_bias_check.py`
  was added as standalone, runnable proof the monitor works.
- **R5**: `Attempt.mastery_score_after` plus `mastery_timeline()` turned the
  mastery metric from a snapshot average into a reconstructable time series,
  rendered as a chart on the learner view.

Each addition is unit-tested (`tests/test_ai_engine.py`,
`tests/test_comparative_study.py`, `tests/test_ethics.py`, `tests/
test_api.py`) and traced in `docs/THESIS_MAPPING.md`.
