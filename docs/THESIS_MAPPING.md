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
| 1 | Investigate AI-driven personalization/adaptivity mechanisms and their technical implementation | `backend/ai_engine/personalization.py` (EMA mastery model, ZPD-based difficulty recommender), `backend/ai_engine/llm_client.py` (LLM integration with graceful degradation), unit-tested in `tests/test_ai_engine.py`; technique comparison table in `docs/TECHNICAL_BACKGROUND.md` §3 |
| 2 | Develop/synthesize design guidelines & frameworks for AI-enhanced gamified training platforms | The architecture itself (`docs/ARCHITECTURE.md`) *is* the synthesized framework: a reusable separation of Gamification Engine / AI Engine / Ethics Layer / Analytics that is domain-agnostic (proven by 3 different training verticals sharing one engine in `backend/seed_data.py`); theoretical grounding (SDT/Flow/ZPD) in `docs/TECHNICAL_BACKGROUND.md` §2 |
| 3 | Comparative analysis of AI-driven vs. traditional gamification | `docs/EVALUATION_FRAMEWORK.md` §1 defines the exact code change (a `condition` flag) needed to run a control/treatment study on this codebase without building a second system, plus hypotheses H1-H3 |
| 4 | Identify/analyze ethical, privacy, fairness issues and propose mitigations | `backend/ethics/privacy.py`, `backend/ethics/bias_mitigation.py`, fully discussed with rationale in `docs/ETHICS_PRIVACY.md`, unit-tested in `tests/test_ethics.py` |
| 5 | Establish metrics/methods for evaluating AI-enhanced gamification impact | `backend/analytics/reporting.py::build_dashboard_metrics`, operationalized as a 3-family metric table (engagement/performance/fairness) in `docs/EVALUATION_FRAMEWORK.md` §2, visualized live on `frontend/dashboard.html` |

## Research Questions → Evidence

### R1 - AI personalization/adaptivity integration
- **Technical mechanism**: `update_mastery()` (real-time performance
  monitoring via EMA) and `difficulty_for_mastery()` (adaptive path
  selection) in `backend/ai_engine/personalization.py`.
- **"More challenging and more enjoyable at the same time"**: operationalized
  as the ZPD-stretch target (always one difficulty band above current
  mastery) - see `docs/TECHNICAL_BACKGROUND.md` §2.3.
- **Effectiveness measurement**: mastery-growth-rate metric in
  `docs/EVALUATION_FRAMEWORK.md` §2.2.

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
- Full comparative protocol, hypotheses, and the minimal code delta needed
  to run it on this exact codebase: `docs/EVALUATION_FRAMEWORK.md` §1.

### R4 - Ethics, privacy, fairness
- Consent gate enforced server-side (`ethics/privacy.py::require_consent`),
  right-to-erasure (`erase_learner`), behaviour-only adaptivity model (no
  demographic conditioning), human-reviewed fairness monitor
  (`bias_mitigation.audit_cohort_fairness`) surfaced on the dashboard.
  Full discussion with explicit trade-offs: `docs/ETHICS_PRIVACY.md`.

### R5 - Metrics and methods
- Concrete metric definitions mapped to database columns (no
  hypothetical instrumentation needed): `docs/EVALUATION_FRAMEWORK.md` §2.
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
