"""
Mastery Model Comparison
========================
Addresses the part of Research Question 1 (R1) that asks for an examination
of "the effectiveness of various AI techniques" - not just implementation of
one. `personalization.py` already implements the EMA estimator used to drive
real difficulty decisions. This module adds a second, independent estimator
(Bayesian Knowledge Tracing) computed in parallel on the same real attempt
data, so the two techniques can be compared empirically rather than just
described theoretically.

Design choice: BKT here is a **shadow metric** - it is computed and stored
for every attempt, but it does not drive difficulty recommendations (EMA
still does, via personalization.py). This keeps the system's real adaptive
behaviour on the simpler, more auditable estimator (consistent with the R4
transparency rationale in TECHNICAL_BACKGROUND.md), while still producing
genuine comparative evidence for R1.

BKT parameters below are illustrative textbook defaults, not fitted to real
learner data - this is an honest limitation worth stating in the thesis: a
production system would calibrate these per skill from historical data.
"""
from dataclasses import dataclass

# Standard BKT parameters (Corbett & Anderson, 1994 - illustrative defaults):
P_TRANSIT = 0.15   # probability of moving from "not known" to "known" after one attempt
P_SLIP = 0.10      # probability of an incorrect answer despite knowing the skill
P_GUESS = 0.20     # probability of a correct answer despite not knowing the skill

DEFAULT_INITIAL_MASTERY_BKT = 0.3  # matches personalization.DEFAULT_INITIAL_MASTERY for a fair comparison


@dataclass
class BKTUpdate:
    new_mastery: float


def bkt_update(*, prior_mastery: float, correct: bool) -> BKTUpdate:
    """
    Standard two-step Bayesian Knowledge Tracing update:
    1. Bayes' rule: revise P(known) given the observed correct/incorrect response.
    2. Learning transition: apply the probability that a learning opportunity
       occurred during this attempt, regardless of the observation.
    """
    p_known = min(max(prior_mastery, 1e-6), 1 - 1e-6)

    if correct:
        numerator = p_known * (1 - P_SLIP)
        denominator = numerator + (1 - p_known) * P_GUESS
    else:
        numerator = p_known * P_SLIP
        denominator = numerator + (1 - p_known) * (1 - P_GUESS)

    p_known_given_obs = numerator / denominator if denominator > 0 else p_known
    p_known_after_transit = p_known_given_obs + (1 - p_known_given_obs) * P_TRANSIT

    return BKTUpdate(new_mastery=round(min(max(p_known_after_transit, 0.0), 1.0), 4))
