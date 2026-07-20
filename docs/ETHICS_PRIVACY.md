# Ethics, Privacy, and Fairness (R4)

Addresses: *"What ethical, privacy, and fairness issues arise with
AI-powered gamified training, and how can they be mitigated?"*

## 1. Issue: informed consent for behavioural data collection

AI-driven adaptivity requires fine-grained behavioural telemetry (every
answer, its correctness, and response time). Without safeguards, this
creates a surveillance dynamic incompatible with a healthy training
relationship.

**Mitigation implemented:**
- `POST /api/consent` (`backend/routers/consent.py`) is the *only* way a
  learner record becomes eligible for data collection.
- `backend/ethics/privacy.py::require_consent` is called at the top of
  every data-writing endpoint (`GET /api/quests`, `POST /api/attempts`,
  `POST /api/quests/generate`) and raises `HTTP 403` if consent is missing
  or was withdrawn/erased. This is enforced **server-side**, so it cannot be
  bypassed by skipping the consent UI screen and calling the API directly -
  a common gap when consent is only a frontend checkbox.
- Every consent decision (grant or withdrawal) is appended to
  `ConsentRecord` as an **immutable audit trail** rather than a single
  mutable boolean, so an organization can demonstrate compliance
  historically, not just show current state.

## 2. Issue: right to erasure / data minimization

Learners may leave the organization or withdraw consent after data has
already been collected.

**Mitigation implemented:**
- `POST /api/privacy/erase` (`backend/ethics/privacy.py::erase_learner`)
  scrubs direct identifiers (`display_name`, `cohort`, `preferences`) and
  sets `erased_at`, after which `require_consent` treats the learner as
  no-longer-consenting for any future writes.
- Aggregate statistics (attempt counts, mastery trends) are deliberately
  **not** hard-deleted, because destroying historical training records
  entirely would corrupt organization-level reporting for *other* learners'
  cohort comparisons. This is a considered trade-off (pseudonymization over
  full deletion) that should be disclosed to learners in the consent
  language, and is a specific, arguable design decision worth defending or
  revisiting in the thesis's ethics discussion.

## 3. Issue: algorithmic bias in adaptive difficulty/feedback

An adaptive system that conditions difficulty or feedback tone on anything
correlated with a protected characteristic could systematically
disadvantage a group (e.g., consistently under-challenging one cohort,
denying them the same mastery growth opportunities).

**Mitigation implemented:**
- The adaptivity model (`backend/ai_engine/personalization.py`) is
  **strictly behaviour-conditioned**: `update_mastery` and
  `difficulty_for_mastery` take only `correctness`/`response_time`/`streak`
  as inputs. `cohort` is never passed into these functions - grep the
  codebase and confirm `cohort` only appears in `models.py`,
  `routers/consent.py`, and `analytics/reporting.py`'s fairness audit, never
  in `ai_engine/`.
- Because the model is auditable and behaviour-only, it cannot *directly*
  encode cohort bias. It could still produce *indirect* disparate impact if,
  for example, one cohort systematically has less practice time - which is
  why a separate **fairness monitor** exists rather than assuming the
  behaviour-blind design is sufficient on its own.
- `backend/ethics/bias_mitigation.py::audit_cohort_fairness` computes each
  cohort's average mastery vs. the overall average and flags deviations
  beyond `DISPARITY_FLAG_THRESHOLD` (15 percentage points). This is
  surfaced on the Instructor Dashboard's "Fairness Monitor" panel.
- **Deliberately not automated**: the audit *flags for human review*, it
  does not auto-correct scores or auto-adjust difficulty. Automatically
  "fixing" a detected disparity without understanding its cause (e.g.,
  unequal access to training time vs. a genuinely harder task) is itself an
  ethical risk this design avoids.

## 4. Issue: manipulation / dark-pattern gamification

Gamification mechanics (streaks, badges, leaderboards) can cross from
motivating into manipulative, e.g., exploiting loss-aversion with fragile
streaks, or creating unhealthy competitive pressure via public leaderboards
in a mandatory-training context.

**Mitigation implemented / design stance:**
- Streak and badge thresholds are small, fixed, and disclosed in the UI
  copy - no hidden variable-ratio reward schedules (the mechanic most
  associated with compulsive-use design in the gamification-ethics
  literature).
- The leaderboard on the instructor dashboard is admin-facing, not
  learner-facing by default in this prototype, reducing peer-pressure
  dynamics for a workplace context where training is often mandatory rather
  than voluntary. If a learner-facing leaderboard is added in a future
  iteration, it should be opt-in per the same consent model used for data
  collection.

## 5. Issue: data governance / retention

**Design stance for a full deployment (beyond this prototype's pilot
scope):** define and document a retention period for `EngagementEvent` and
`Attempt` rows, encrypt the SQLite file or migrate to an encrypted-at-rest
managed database, and restrict `/api/dashboard/metrics` and
`/api/learners/{id}/profile` behind organizational authentication (this
prototype intentionally omits auth/access-control to stay focused on the
gamification/AI/ethics architecture, but a real deployment must add it
before handling real employee data).

## 6. Summary table

| Risk | Mitigation | Code location |
|---|---|---|
| Data collected without consent | Server-side consent gate on every write endpoint | `ethics/privacy.py::require_consent` |
| No audit trail of consent state | Append-only `ConsentRecord` | `models.py::ConsentRecord` |
| No way to withdraw / be forgotten | Pseudonymizing erasure endpoint | `ethics/privacy.py::erase_learner` |
| Adaptive model encodes group bias | Behaviour-only inputs to mastery model | `ai_engine/personalization.py` |
| Undetected disparate impact | Cohort fairness monitor (human-reviewed) | `ethics/bias_mitigation.py` |
| Manipulative reward mechanics | Fixed, disclosed, non-exploitative thresholds | `gamification/engine.py` |
