import os
import uuid

import pytest


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test_skillsphere.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Reload config/database/main so they pick up the test DB path.
    import importlib
    from backend import config, database
    importlib.reload(config)
    importlib.reload(database)
    from backend import main
    importlib.reload(main)

    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


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

    # Right to erasure.
    resp = client.post(f"/api/privacy/erase?learner_id={learner_id}")
    assert resp.status_code == 200
    resp = client.get(f"/api/learners/{learner_id}/profile")
    assert resp.json()["learner"]["display_name"] == "erased-learner"
