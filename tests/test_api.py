import uuid

import pytest


@pytest.fixture(scope="module")
def client():
    # tests/conftest.py sets DATABASE_URL before any backend module is
    # imported, so a plain import here already targets an isolated test DB -
    # no importlib.reload() needed.
    from backend import main
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


def _force_condition(learner_id: str, condition: str) -> None:
    """Test-only helper: the app deliberately has no API to set `condition`
    directly (it must be randomly assigned to avoid self-selection bias in
    the R3 comparative study), so tests that need a specific branch reach
    into the DB directly rather than looping consent calls until they get
    lucky."""
    from backend.database import SessionLocal
    from backend import models
    db = SessionLocal()
    try:
        learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
        learner.condition = condition
        db.commit()
    finally:
        db.close()


def test_full_gameplay_loop(client):
    learner_id = f"test_{uuid.uuid4().hex[:8]}"

    # Ethics gate: attempting to fetch quests before consent must fail.
    resp = client.get(f"/api/quests?learner_id={learner_id}")
    assert resp.status_code == 403

    # Grant consent.
    resp = client.post("/api/consent", json={
        "learner_id": learner_id, "display_name": "Test Learner",
        "cohort": "team-test", "consent": True,
    })
    assert resp.status_code == 200
    assert resp.json()["consent_given"] is True
    assert resp.json()["condition"] in ("treatment", "control")

    # This test exercises the full AI-driven (treatment) happy path;
    # R3 branching itself is covered by test_comparative_study.py.
    _force_condition(learner_id, "treatment")

    # Now quests should be recommended (one per seeded module).
    resp = client.get(f"/api/quests?learner_id={learner_id}")
    assert resp.status_code == 200
    quests = resp.json()
    assert len(quests) == 4

    quest = quests[0]
    # Submit an attempt (may be right or wrong; both paths must work).
    resp = client.post("/api/attempts", json={
        "learner_id": learner_id, "quest_id": quest["id"],
        "selected_index": 0, "response_time_ms": 2000,
    })
    assert resp.status_code == 200
    result = resp.json()
    assert "ai_feedback" in result and result["ai_feedback"]
    assert 0.0 <= result["mastery_score"] <= 1.0

    # Profile should now reflect the attempt.
    resp = client.get(f"/api/learners/{learner_id}/profile")
    assert resp.status_code == 200
    profile = resp.json()
    assert len(profile["recent_history"]) == 1
    # GET /api/quests seeds a SkillMastery row per module (one per skill) so it
    # can recommend a difficulty for each; only the attempted skill has an attempt.
    assert len(profile["skills"]) == 4
    attempted_skill = next(s for s in profile["skills"] if s["skill"] == quest["skill"])
    assert attempted_skill["attempts_count"] == 1
    assert "mastery_score_bkt" in attempted_skill

    # AI scenario generation should return a well-formed quest.
    resp = client.post("/api/quests/generate", json={"learner_id": learner_id, "skill": "data_privacy"})
    assert resp.status_code == 200
    generated = resp.json()
    assert len(generated["options"]) >= 2

    # Dashboard metrics should include this learner.
    resp = client.get("/api/dashboard/metrics")
    assert resp.status_code == 200
    metrics = resp.json()
    assert metrics["total_learners"] >= 1
    assert metrics["total_attempts"] >= 1
    assert "technique_comparison" in metrics

    # Right to erasure.
    resp = client.post(f"/api/privacy/erase?learner_id={learner_id}")
    assert resp.status_code == 200
    resp = client.get(f"/api/learners/{learner_id}/profile")
    assert resp.json()["learner"]["display_name"] == "erased-learner"


def test_control_condition_gets_static_feedback_and_no_ai_generation(client):
    learner_id = f"test_control_{uuid.uuid4().hex[:8]}"
    client.post("/api/consent", json={
        "learner_id": learner_id, "display_name": "Control Learner", "consent": True,
    })
    _force_condition(learner_id, "control")

    quests = client.get(f"/api/quests?learner_id={learner_id}").json()
    quest = quests[0]

    resp = client.post("/api/attempts", json={
        "learner_id": learner_id, "quest_id": quest["id"],
        "selected_index": quest["options"].index(quest["options"][0]), "response_time_ms": 1000,
    })
    assert resp.status_code == 200
    assert resp.json()["ai_feedback"] in ("Correct.", "Incorrect.")

    # Control learners don't get on-demand AI scenario generation.
    resp = client.post("/api/quests/generate", json={"learner_id": learner_id, "skill": "data_privacy"})
    assert resp.status_code == 403


def test_treatment_condition_gets_personalized_feedback(client):
    learner_id = f"test_treatment_{uuid.uuid4().hex[:8]}"
    client.post("/api/consent", json={
        "learner_id": learner_id, "display_name": "Treatment Learner", "consent": True,
    })
    _force_condition(learner_id, "treatment")

    quests = client.get(f"/api/quests?learner_id={learner_id}").json()
    quest = quests[0]

    resp = client.post("/api/attempts", json={
        "learner_id": learner_id, "quest_id": quest["id"], "selected_index": 0, "response_time_ms": 1000,
    })
    assert resp.status_code == 200
    # Treatment feedback is never the bare control template.
    assert resp.json()["ai_feedback"] not in ("Correct.", "Incorrect.")


def test_comparison_endpoint_returns_both_conditions(client):
    resp = client.get("/api/dashboard/comparison")
    assert resp.status_code == 200
    data = resp.json()
    assert "control" in data and "treatment" in data
    assert "note" in data
