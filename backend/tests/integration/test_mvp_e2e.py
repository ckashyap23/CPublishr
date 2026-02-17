from __future__ import annotations

from fastapi.testclient import TestClient

from src.db.init_db import create_all
from src.db.session import get_engine, init_engine
from src.main import app


def _client() -> TestClient:
    init_engine()
    engine = get_engine()
    assert "sqlite" not in str(engine.url), "Tests must run against DATABASE_URL from .env (Postgres)"
    create_all(engine)
    return TestClient(app)


def test_mvp_end_to_end_minimal_flow() -> None:
    client = _client()
    project_id = "proj_mvp_e2e"

    payload = {
        "project_id": project_id,
        "topic_title": "AI workflow MVP",
        "core_idea": "One master doc and predictable adapters.",
        "user_content": "Use this as optional seed context from the user.",
        "target_audience": "builders",
        "content_depth": "surface",
        "tone_preference": "professional",
        "distribution_targets": ["linkedin", "x", "medium", "github"],
    }

    r = client.post("/api/v1/projects/", json=payload)
    assert r.status_code == 200

    r = client.post("/api/v1/workflows/runs", json={"project_id": project_id})
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_editorial"

    versions = client.get(f"/api/v1/versions/{project_id}")
    outputs = client.get(f"/api/v1/platform-outputs/{project_id}")
    assert versions.status_code == 200
    assert outputs.status_code == 200
    assert len(versions.json()["versions"]) >= 1
    assert outputs.json()["outputs"] == []

    latest_v = versions.json()["versions"][-1]["version_number"]
    r = client.post(
        "/api/v1/workflows/nodes/editorial",
        json={
            "project_id": project_id,
            "current_version": latest_v,
            "editor_actions": [{"action": "simplify", "target_section": "Conclusion"}],
            "user_feedback": "Shorten wording",
        },
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/publishing/jobs",
        json={"platform": "linkedin", "content_payload": {"project_id": project_id}, "scheduled_time": None},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "published"
    assert r.json()["external_id"]
