# Evaluation Framework (R3 + R5)

Addresses:
- **R3**: *"How do AI-driven gamification approaches compare with
  traditional (non-AI) gamified training in terms of motivation, engagement,
  and learning performance?"*
- **R5**: *"What metrics and methods should be used to evaluate the impact
  of AI-enhanced gamification on corporate learning?"*

## 1. Comparative study design (R3)

The prototype's architecture makes an A/B comparison possible **without
building a second system**: the AI Engine has a built-in, deterministic
"fallback mode" (`backend/ai_engine/llm_client.py`) that already implements
a *non-adaptive baseline* when `ANTHROPIC_API_KEY` is unset - but that alone
only removes generative content, not adaptivity. For a proper comparative
study, define two conditions using a feature flag on top of the existing
code:

| Condition | Difficulty selection | Feedback | Content |
|---|---|---|---|
| **Control (traditional gamified)** | Fixed linear progression (module order, no mastery lookup) | Static templated message ("Correct"/"Incorrect") | Only seeded `Quest` rows, no generation |
| **Treatment (AI-driven)** | `difficulty_for_mastery()` ZPD-based recommendation | LLM-personalized feedback via `chat_complete` | AI-generated scenarios via `generate_scenario` available on demand |

**Implementation note:** add a `condition` field to `Learner` (`control` /
`treatment`), randomly assigned at consent time, and branch
`routers/quests.py::recommended_quests` and
`routers/gameplay.py::submit_attempt` to skip the adaptive/AI calls for
`control` learners (module-order difficulty, `fallback_feedback` only). This
is a small, additive change to the existing router logic - the Gamification
Engine and data schema do not need to change, which is exactly the value of
having isolated the AI Engine as a swappable component from day one.

### 1.1 Suggested study protocol
1. **Random assignment** at signup (consent screen) to control/treatment,
   stratified by `cohort` if cohorts represent intact teams (to avoid
   contamination between conditions on the same team).
2. **Pre-test**: baseline quiz on all three seeded skills before any
   training, to compute learning *gain* rather than raw post-test score.
3. **Training period**: fixed duration or fixed number of quests, identical
   across conditions.
4. **Post-test + validated motivation/engagement survey** (e.g., adapted
   Intrinsic Motivation Inventory items for autonomy/competence, mapped to
   the SDT background in `docs/TECHNICAL_BACKGROUND.md`), administered via
   Qualtrics/Google Forms per the original technical-demo plan.
5. **Analysis**: between-groups comparison (t-test / Mann-Whitney depending
   on distribution) on learning gain, self-reported engagement, and the
   system-logged engagement metrics below - triangulating self-report with
   behavioural telemetry is itself a methodological contribution, since pure
   self-report is a known weak point in gamification research.

### 1.2 What "AI adds" - specific, falsifiable hypotheses
- H1: Treatment learners show higher **mastery growth rate**
  (Δmastery/attempt) than control, because ZPD-targeted difficulty keeps
  them in a productive-struggle zone rather than a fixed curriculum order.
- H2: Treatment learners show higher **completion rate** and lower
  **drop-off** (fewer sessions with zero attempts after day 1), attributable
  to personalized feedback sustaining motivation (SDT: competence).
- H3: Treatment and control show **no significant fairness difference**
  across cohorts (validates that AI adaptivity does not introduce new
  disparities relative to the non-AI baseline) - this directly operationalizes R4.

## 2. Evaluation metrics and methods (R5)

Three metric families, each with a concrete source in the existing schema
(`backend/models.py`) - no new instrumentation is required to start
collecting them:

### 2.1 Engagement metrics
| Metric | Definition | Source |
|---|---|---|
| Session frequency | Distinct calendar days with ≥1 `EngagementEvent` | `EngagementEvent.timestamp` |
| Completion rate | Attempts / quests recommended, per module | `Attempt` vs. `Quest` |
| Time-on-task | `response_time_ms` distribution | `Attempt.response_time_ms` |
| Streak length | Longest `correct_streak` reached | `SkillMastery.correct_streak` |
| Retention | % of learners active in week N vs. week 1 | `EngagementEvent` grouped by ISO week |

`backend/analytics/reporting.py::build_dashboard_metrics` already computes a
14-day engagement time series and active-learner counts as a starting
implementation of this table.

### 2.2 Learning performance metrics
| Metric | Definition | Source |
|---|---|---|
| Overall accuracy | Mean correctness across attempts | `Attempt.correct` |
| Mastery growth | Δ`mastery_score` over time, per skill | `SkillMastery` history (extend `Attempt` query by timestamp) |
| Time-to-mastery | Attempts until `mastery_score ≥ 0.85` | Derived from `Attempt` + `SkillMastery` |
| Transfer/generalization | Accuracy on **AI-generated** vs. seeded scenarios for the same skill | `Quest.generated_by_ai` flag already present |

### 2.3 Fairness / responsible-AI metrics (bridges to R4)
| Metric | Definition | Source |
|---|---|---|
| Cross-cohort mastery gap | \|cohort avg − overall avg\| | `ethics/bias_mitigation.py::audit_cohort_fairness` |
| Consent rate | % of signups that grant consent | `ConsentRecord` |
| Erasure requests | Count and time-to-fulfillment | `Learner.erased_at` |

### 2.4 Continuous improvement loop
The Instructor Dashboard (`frontend/dashboard.html`) is the operational
half of R5's "how can evaluation approaches provide continuous
improvement": engagement/fairness metrics refresh every 15 seconds from
live data, so instructors can identify, e.g., a module with unusually low
completion or a flagged cohort disparity **during** a training rollout, not
only in a post-hoc research report. In an evaluation write-up, this
dashboard doubles as the study's real-time monitoring instrument.

## 3. Validity considerations

- **Novelty effect**: an initial engagement boost from AI features may fade;
  the study protocol above should run long enough (multi-week) to
  distinguish genuine motivational gains from novelty.
- **Instrumentation validity**: `response_time_ms` is measured client-side
  (`Date.now()` deltas in `frontend/js/app.js`) and can be inflated by
  distractions outside the system's control - treat it as a noisy proxy, not
  a precise measure of cognitive effort.
- **Small-N pilot caveat**: with a pilot-scale deployment (tens of
  learners), prefer non-parametric tests and report effect sizes alongside
  p-values, and treat the fairness monitor's flags as *hypotheses to
  investigate qualitatively*, not statistically powered conclusions.
