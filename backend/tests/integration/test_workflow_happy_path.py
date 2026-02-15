from __future__ import annotations

import json

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


def test_happy_path_topic_to_outputs_and_editorial_and_publish_job() -> None:
    client = _client()

    project_id = "proj_test_1"
    node0_payload = {
        "project_id": project_id,
        "topic_title": "AI agents for content",
        "core_idea": "One master doc, many platform-native variants.",
        "target_audience": "builders",
        "content_depth": "intermediate",
        "tone_preference": "professional",
        "distribution_targets": ["linkedin", "x", "medium", "github"],
    }

    # Node 0 (projects init)
    r = client.post("/api/v1/projects/", json=node0_payload)
    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == project_id
    assert "context_bundle" in body

    # Node 1
    r = client.get(f"/api/v1/workflows/nodes/research/{project_id}")
    assert r.status_code == 200
    assert "research_summary" in r.json()

    # Node 2
    r = client.get(f"/api/v1/workflows/nodes/master/{project_id}")
    assert r.status_code == 200
    assert "master_document" in r.json()

    # Versions list
    r = client.get(f"/api/v1/versions/{project_id}")
    assert r.status_code == 200
    versions = r.json()["versions"]
    assert len(versions) >= 1
    assert versions[-1]["content"]

    # Full workflow run (uses stored Node 0 bundle)
    r = client.post("/api/v1/workflows/runs", json={"project_id": project_id})
    assert r.status_code == 200
    run = r.json()
    assert run["run_id"]
    assert run["status"] in {"completed", "completed_with_editorial"}

    # Platform outputs list
    r = client.get(f"/api/v1/platform-outputs/{project_id}")
    assert r.status_code == 200
    outputs = r.json()["outputs"]
    assert len(outputs) >= 1
    # content is stored as JSON string
    json.loads(outputs[0]["content"])

    # Editorial (Node 3) based on latest version number
    latest_version = versions[-1]["version_number"]
    editorial_payload = {
        "project_id": project_id,
        "current_version": latest_version,
        "editor_actions": [{"action": "rewrite", "target_section": "Framework"}],
        "user_feedback": "Make it more concise.",
    }
    r = client.post("/api/v1/workflows/nodes/editorial", json=editorial_payload)
    assert r.status_code == 200
    ed = r.json()
    assert ed["draft_version"] == latest_version + 1
    assert "updated_master_document" in ed

    # Publish job create (job is persisted but contract returns only status/external_id)
    r = client.post(
        "/api/v1/publishing/jobs",
        json={"platform": "linkedin", "content_payload": {"project_id": project_id}, "scheduled_time": None},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "published"


