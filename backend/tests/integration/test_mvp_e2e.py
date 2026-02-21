from __future__ import annotations

from fastapi.testclient import TestClient
from uuid import uuid4

from src.db.init_db import create_all
from src.db.session import get_engine, init_engine
from src.main import app


def _client() -> TestClient:
    init_engine()
    engine = get_engine()
    assert "sqlite" not in str(engine.url), "Tests must run against DATABASE_URL from .env (Postgres)"
    create_all(engine)
    return TestClient(app)


def _auth(client: TestClient) -> tuple[dict[str, str], str]:
    slug = uuid4().hex[:10]
    email = f"tester_{slug}@example.com"
    res = client.post(
        "/api/v1/auth/signup",
        json={"user_id": f"usr_{slug}", "email": email, "password": "Passw0rd123"},
    )
    assert res.status_code == 200
    data = res.json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}, data["default_voice_profile_id"]


def test_mvp_end_to_end_minimal_flow() -> None:
    client = _client()
    headers, voice_profile_id = _auth(client)
    project_id = f"proj_mvp_e2e_{uuid4().hex[:8]}"

    payload = {
        "project_id": project_id,
        "topic_title": "AI workflow MVP",
        "core_idea": "One master doc and predictable adapters.",
        "user_content": "Use this as optional seed context from the user.",
        "target_audience": {"primary_segment": "builders_developers", "notes": None},
        "detail_level": "quick_take",
        "tone_preference": "professional",
        "voice_profile_id": voice_profile_id,
        "distribution_targets": ["linkedin", "x", "medium", "github"],
    }

    r = client.post("/api/v1/projects/", json=payload, headers=headers)
    assert r.status_code == 200

    r = client.post("/api/v1/workflows/runs", json={"project_id": project_id}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_editorial"

    versions = client.get(f"/api/v1/versions/{project_id}", headers=headers)
    outputs = client.get(f"/api/v1/platform-outputs/{project_id}", headers=headers)
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
        headers=headers,
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/publishing/jobs",
        json={"platform": "linkedin", "content_payload": {"project_id": project_id}, "scheduled_time": None},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "published"
    assert r.json()["external_id"]
