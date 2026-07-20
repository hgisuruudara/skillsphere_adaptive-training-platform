# Technical Background

This document provides the theoretical and technical foundations that
justify the design decisions in `docs/ARCHITECTURE.md`. It is written to be
usable directly as thesis background/literature-grounding material (Chapter
2-style), connecting established theory to concrete implementation choices
in this codebase.

## 1. Gamification in corporate training

Gamification applies game-design elements (points, levels, badges, quests,
leaderboards) to non-game contexts to increase motivation and engagement.
In corporate training specifically, gamification frameworks historically
focus on generic engagement mechanics without addressing the constraints
unique to workplace learning: compliance requirements, adult-learning
principles, time-pressured schedules, and measurable ROI to the
organization. This is precisely the gap identified in the research
proposal - existing frameworks "often do not incorporate AI integration,
adaptive systems, or the needs of corporate training contexts" (Pistono, et
al., 2024), motivating the need for a new framework rather than reuse of a
generic one (Alfaqiri, et al., 2022).

**Implementation:** `backend/gamification/engine.py` implements the
mechanical core (points, level curve, badges) as pure functions decoupled
from any specific domain, so the *same* engine can be pointed at different
corporate training verticals (safety, service, compliance - see
`backend/seed_data.py`) without modification, addressing the
framework-reusability gap directly.

## 2. Motivational theory underpinning the design

Three theories jointly justify why the system is structured the way it is:

### 2.1 Self-Determination Theory (SDT)
SDT (Deci & Ryan) holds that motivation is driven by three psychological
needs: **autonomy**, **competence**, and **relatedness**. Mapped onto
SkillSphere:
- *Autonomy* - learners choose which recommended quest to attempt and can
  request a freshly AI-generated scenario on demand (`generateBtn` in
  `frontend/js/app.js`) rather than following a fixed linear path.
- *Competence* - the mastery score and difficulty progression give
  continuous, legible feedback on skill growth (`SkillMastery.mastery_score`).
- *Relatedness* - the leaderboard and cohort view on the instructor
  dashboard situate individual progress within a team/organizational context.

### 2.2 Flow Theory (Csikszentmihalyi)
Flow - a state of deep engagement - occurs when perceived challenge closely
matches perceived skill. Too easy → boredom; too hard → anxiety. This is
*directly* implemented, not just referenced: `difficulty_for_mastery()` in
`backend/ai_engine/personalization.py` maps a learner's mastery score onto a
difficulty band that is always one notch above current mastery, keeping the
learner near the challenge/skill balance point rather than at the extremes.

### 2.3 Zone of Proximal Development (ZPD, Vygotsky)
ZPD describes the gap between what a learner can do alone and what they can
do with the right support/scaffolding. The AI Engine's difficulty
recommendation is explicitly framed as a ZPD "stretch" target: it recommends
content the learner cannot yet answer with full confidence but is
positioned to succeed at, rather than content matched exactly to current
ability. This is what separates true *adaptivity* from simple linear
progression.

Together, SDT/Flow/ZPD provide the theoretical justification the research
gap calls for: "design guidelines... based on established theories such as
self determination theory, flow theory, and the zone of proximal
development" (R2).

## 3. AI techniques for personalization and adaptivity (R1)

The proposal asks for an examination of "technical approaches,
implementation strategies, and effectiveness of various AI techniques."
Three broad families exist in the literature, and it's important to be
explicit about which one this prototype uses and why:

| Technique | How it works | Interpretability | Data requirement | Used here? |
|---|---|---|---|---|
| **Item Response Theory (IRT) / Bayesian Knowledge Tracing** | Probabilistic model of latent skill vs. item difficulty, updated per response | High | Moderate (needs item calibration data) | Approximated via EMA (see below) |
| **Exponential Moving Average (EMA) mastery tracking** | `new = old + α(observed - old)`, a lightweight recency-weighted estimator | Very high - one formula, fully auditable | Minimal - works from attempt 1 | **Yes** - `update_mastery()` |
| **Reinforcement Learning (RL) policies** | An agent learns a difficulty/content policy that maximizes long-run engagement/learning reward | Low (learned policy is a black box) | High (needs large interaction volume) | No - deliberately avoided for a pilot-scale, auditable system |
| **LLM-based generation** | A large language model generates novel scenario text/feedback conditioned on learner context | Medium (output is human-readable but reasoning is opaque) | None (zero-shot) | **Yes** - `scenario_generator.py`, feedback generation in `personalization.py` |

**Design rationale:** the mastery/difficulty model uses the transparent EMA
approach rather than RL or full IRT for two reasons directly tied to the
thesis's other objectives: (1) auditability supports the ethics/fairness
objective (R4) - a regulator or instructor can hand-verify the update rule;
and (2) it works from the very first attempt, which matters for a
time-boxed pilot study (R3) where learners will not generate enough data for
RL or IRT calibration to converge. The **generative** side of "AI" (content
and feedback) is where the LLM is actually used, since natural-language
generation is a task where LLMs meaningfully outperform template systems,
while the **decision** side (what to show next) is kept simple and
inspectable on purpose.

This split - transparent decision logic + generative LLM content - is the
prototype's answer to the research gap around unclear framework guidance
for combining AI and gamification (Lamnai & Elmhouti, 2025; Pérez, et al.,
2023).

## 4. Large Language Models as a content/feedback engine

The `LLM-Based AI Engine` box uses the Anthropic Claude Messages API
(configurable, default `claude-opus-4-8`) for two generative tasks:

1. **Adaptive feedback** (`personalization.build_feedback_prompt`) -
   conditions the model on the learner's mastery score, the skill, the
   question, and correctness, instructing it to adjust tone (more
   supportive at low mastery, more challenging at high mastery). This is
   prompt-engineered personalization rather than fine-tuning, appropriate
   for a prototype where per-organization fine-tuning would be
   disproportionate.
2. **Scenario generation** (`scenario_generator.generate_scenario`) -
   generates a structured JSON workplace scenario (prompt + 4 options +
   correct index) at a target difficulty, so the Training Content
   Repository can grow beyond its seeded items without manual authoring.

Both call sites go through `backend/ai_engine/llm_client.py`, which
**always** degrades to a deterministic offline generator on any error or
missing API key. This is a technical background point worth stating
explicitly for a thesis: it means the system's core adaptive/gamified loop
does not have a hard dependency on a third-party API's availability,
pricing, or rate limits - relevant to any later discussion of
deployment risk or cost in a corporate setting.

## 5. Serious games vs. gamification

The proposal's title bundles "gamification and serious games." The
distinction matters technically: gamification adds game *elements* to an
existing activity (what SkillSphere's Gamification Engine does to quizzes),
while a serious game is a complete game built primarily for a non-
entertainment purpose (the scenario-based "quests" in this prototype - e.g.
`q_safety_4`, a branching workplace-safety scenario - sit closer to this
end of the spectrum). SkillSphere intentionally spans both: `kind: "quiz"`
items are gamified assessment, `kind: "scenario"` items are minimal serious-
game vignettes. This lets the comparative study (R3) later isolate whether
gains come from gamification mechanics, scenario-based serious-game design,
AI adaptivity, or their combination.

## 6. Ethical AI and data governance background

AI systems that "collect and analyse a lot of detailed data about learner
behaviours and performances" (as the research gaps note) raise three
distinct concerns, each with a corresponding technical control in this
codebase (elaborated in `docs/ETHICS_PRIVACY.md`):

- **Privacy** - consent must be explicit and precede data collection →
  `backend/ethics/privacy.py::require_consent` is enforced at the API layer,
  not just the UI, so it cannot be bypassed by a direct API call.
- **Algorithmic bias / fairness** - an adaptive system could inadvertently
  disadvantage a group if it conditions on demographic-like signals →
  the mastery model is behaviour-only (never reads `cohort`), and a
  separate fairness-*monitoring* (not correcting) module audits outcomes
  across cohorts for human review (Shahad, et al., 2025).
- **Manipulation / dark patterns** - gamification can be used to manipulate
  rather than motivate (e.g., exploitative streak mechanics) → badge and
  streak mechanics here are transparent, capped, and disclosed in the UI
  copy rather than hidden variable-reward schedules.

## 7. Evaluation background

Standardized metrics for AI-enhanced gamification are noted as
underdeveloped (Albaladejo-González, et al., 2025; Koivisto, et al., 2022).
`docs/EVALUATION_FRAMEWORK.md` operationalizes three metric families -
engagement, learning performance, and fairness - directly from the fields
already captured in `backend/models.py` (`EngagementEvent`, `Attempt`,
`SkillMastery`), so metric collection is not an afterthought bolted onto
the system after data collection design, but built into the schema from the
start.
