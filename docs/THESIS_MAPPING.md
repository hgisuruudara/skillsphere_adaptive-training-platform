# Thesis Traceability Matrix

This document is the direct answer to "how does this prototype serve as
evidence for the thesis." It maps every research objective and research
question to specific, runnable code, so a thesis chapter (e.g., "System
Design and Implementation" or "Evidence of Feasibility") can cite exact
file/function references rather than describing the system only in the
abstract.

## Research Objectives → Evidence

| # | Objective | Evidence in this repository |
|---|---|---|
| 1 | Investigate AI-driven personalization/adaptivity mechanisms and their technical implementation | `backend/ai_engine/personalization.py` (EMA mastery model, ZPD-based difficulty recommender, past-mistake-aware feedback), `backend/ai_engine/mastery_models.py` (Bayesian Knowledge Tracing as a second, independently-computed estimator), `backend/ai_engine/llm_client.py` (LLM integration with graceful degradation), unit-tested in `tests/test_ai_engine.py`; the two estimators are compared on real attempt data via `analytics/reporting.py::_technique_comparison`, surfaced live on the Instructor Dashboard; technique comparison discussion in `docs/TECHNICAL_BACKGROUND.md` §3 |
| 2 | Develop/synthesize design guidelines & frameworks for AI-enhanced gamified training platforms | The architecture itself (`docs/ARCHITECTURE.md`) *is* the synthesized framework: a reusable separation of Gamification Engine / AI Engine / Ethics Layer / Analytics that is domain-agnostic (proven by 4 different training verticals - safety, service, data privacy, onboarding compliance - sharing one engine in `backend/seed_data.py`); theoretical grounding (SDT/Flow/ZPD) in `docs/TECHNICAL_BACKGROUND.md` §2 |
| 3 | Comparative analysis of AI-driven vs. traditional gamification | Implemented, not just designed: `Learner.condition` (`treatment`/`control`) is randomly assigned at consent time and branches `routers/quests.py` and `routers/gameplay.py` end-to-end (adaptive vs. fixed difficulty, LLM feedback vs. static template, on-demand generation vs. seeded-only). `analytics/reporting.py::comparative_study_stats` reports per-condition mastery growth, accuracy, and a Cohen's d effect size, exposed at `GET /api/dashboard/comparison`. Full protocol and hypotheses H1-H3 in `docs/EVALUATION_FRAMEWORK.md` §1 |
| 4 | Identify/analyze ethical, privacy, fairness issues and propose mitigations | `backend/ethics/privacy.py`, `backend/ethics/bias_mitigation.py` (cohort fairness flag now requires both a practical gap *and* statistical significance via a from-scratch Welch's t-test), `scripts/synthetic_bias_check.py` (runnable evidence the monitor catches an injected disparity and stays quiet on a fair one), fully discussed with rationale in `docs/ETHICS_PRIVACY.md`, unit-tested in `tests/test_ethics.py` |
| 5 | Establish metrics/methods for evaluating AI-enhanced gamification impact | `backend/analytics/reporting.py::build_dashboard_metrics` plus `mastery_timeline()` (full per-skill mastery-over-time series, not just a snapshot average), operationalized as a 3-family metric table (engagement/performance/fairness) in `docs/EVALUATION_FRAMEWORK.md` §2, visualized live on `frontend/dashboard.html` and as a per-skill growth chart on the learner view (`frontend/index.html`) |

## Research Questions → Evidence

### R1 - AI personalization/adaptivity integration
- **Technical mechanism**: `update_mastery()` (real-time performance
  monitoring via EMA) and `difficulty_for_mastery()` (adaptive path
  selection) in `backend/ai_engine/personalization.py`.
- **Technique comparison**: `bkt_update()` in `backend/ai_engine/
  mastery_models.py` computes a second mastery estimate (Bayesian Knowledge
  Tracing) on the same evidence in parallel, as a shadow metric that never
  drives gameplay. `analytics/reporting.py::_technique_comparison` reports
  the two estimators' mean absolute difference and agreement rate on real
  attempt data - direct empirical evidence for R1's "effectiveness of
  various AI techniques" rather than a literature comparison alone.
- **Personalization depth**: adaptive feedback references the learner's
  most recent *specific* past mistake on the same skill, not just a
  difficulty number (`gameplay.py::submit_attempt`'s `previous_mistake`
  lookup, `personalization.build_feedback_prompt`).
- **"More challenging and more enjoyable at the same time"**: operationalized
  as the ZPD-stretch target (always one difficulty band above current
  mastery) - see `docs/TECHNICAL_BACKGROUND.md` §2.3.
- **Effectiveness measurement**: mastery-growth-rate metric in
  `docs/EVALUATION_FRAMEWORK.md` §2.2, backed by a full per-skill
  mastery-over-time series (`analytics/reporting.py::mastery_timeline`),
  not just a before/after snapshot.

### R2 - Design guidelines/frameworks
- **Structure**: `docs/ARCHITECTURE.md` component table + diagrams,
  directly derived from (and validating) the thesis's own proposed
  architecture diagram.
- **Theoretical basis**: SDT, Flow, ZPD explicitly connected to specific
  code behaviours in `docs/TECHNICAL_BACKGROUND.md` §2, not just cited in
  the abstract.
- **Game element selection for corporate context**: `docs/
  TECHNICAL_BACKGROUND.md` §5 (gamification vs. serious games distinction,
  with both `kind: "quiz"` and `kind: "scenario"` items implemented).

### R3 - AI-driven vs. traditional gamification
- Full comparative protocol, hypotheses, and the now-implemented condition
  branching: `docs/EVALUATION_FRAMEWORK.md` §1. Random assignment happens
  in `routers/consent.py`; the two conditions genuinely diverge in
  `routers/quests.py::recommended_quests`/`generate_new_scenario` and
  `routers/gameplay.py::submit_attempt` (fixed vs. ZPD-based difficulty,
  static vs. LLM-personalized feedback, no generation vs. on-demand
  generation). `GET /api/dashboard/comparison` reports both groups' mastery
  growth, accuracy, and a Cohen's d effect size.

### R4 - Ethics, privacy, fairness
- Consent gate enforced server-side (`ethics/privacy.py::require_consent`),
  right-to-erasure (`erase_learner`), behaviour-only adaptivity model (no
  demographic conditioning), human-reviewed fairness monitor
  (`bias_mitigation.audit_cohort_fairness`) surfaced on the dashboard.
- **Statistical rigor**: a cohort is only flagged when its mastery gap is
  both practically significant (≥15 points) *and* statistically significant
  (Welch's t-test, p < 0.05, implemented from scratch in
  `bias_mitigation.py` with no scipy dependency) - a fixed threshold alone
  can flag small-sample noise as if it were bias.
- **Runnable proof the monitor works**: `scripts/synthetic_bias_check.py`
  feeds a fair scenario and a deliberately biased scenario through the real
  `audit_cohort_fairness()` function and asserts it distinguishes them -
  the console output is meant to be pasted directly into the thesis as
  fairness-mitigation evidence (see `docs/ETHICS_PRIVACY.md` §3).
  Full discussion with explicit trade-offs: `docs/ETHICS_PRIVACY.md`.

### R5 - Metrics and methods
- Concrete metric definitions mapped to database columns (no
  hypothetical instrumentation needed): `docs/EVALUATION_FRAMEWORK.md` §2.
- **Mastery-over-time evidence**: every `Attempt` now stores the EMA mastery
  score immediately after it was made (`Attempt.mastery_score_after`), so
  `analytics/reporting.py::mastery_timeline` can reconstruct a genuine
  per-skill growth curve instead of asserting growth from two endpoints.
  Rendered as a line chart on the learner view (`frontend/index.html`,
  `js/app.js::renderMasteryChart`) - a screenshot of a learner's own
  mastery curve is direct, individual-level R5 evidence.
- Continuous-improvement mechanism: live-refreshing instructor dashboard
  (`frontend/dashboard.html`, `js/dashboard.js`), discussed in §2.4.

## How to use this matrix in the thesis document

1. **System Design chapter**: cite `docs/ARCHITECTURE.md` for diagrams and
   `docs/TECHNICAL_BACKGROUND.md` for theoretical justification.
2. **Methodology chapter**: cite `docs/DEVELOPMENT_GUIDE.md` for how the
   artifact was constructed, and `docs/EVALUATION_FRAMEWORK.md` §1 for the
   planned comparative study protocol.
3. **Ethics/Fairness chapter**: cite `docs/ETHICS_PRIVACY.md` in full.
4. **Results/Evaluation chapter** (once a pilot is run): report against the
   exact metric tables in `docs/EVALUATION_FRAMEWORK.md` §2 so results map
   cleanly back to the research questions rather than being computed ad hoc.
5. **Appendix**: include `tests/` output (`python -m pytest -q`) as evidence
   the described mechanisms are implemented and behave as specified, not
   just designed on paper.
