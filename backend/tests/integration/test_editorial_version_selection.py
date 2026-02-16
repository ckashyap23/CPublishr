from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from src.contracts.prd import EditorialResponse
from src.db.init_db import create_all
from src.db.repositories.content_repository import ContentRepository
from src.db.session import SessionLocal, get_engine, init_engine
from src.main import app
from src.services.orchestration.engine import OrchestrationEngine
from src.utils.ids import new_id


def _client() -> TestClient:
    init_engine()
    engine = get_engine()
    assert "sqlite" not in str(engine.url), "Tests must run against DATABASE_URL from .env (Postgres)"
    create_all(engine)
    return TestClient(app)


def _seed_version(
    project_id: str,
    *,
    version_number: int,
    version_kind: str,
    content: str,
    variant_label: str | None = None,
) -> None:
    with SessionLocal() as db:
        repo = ContentRepository(db)
        repo.create_version(
            version_id=new_id("ver"),
            project_id=project_id,
            content=content,
            version_number=version_number,
            version_kind=version_kind,
            variant_label=variant_label,
        )


def test_workflow_run_editorial_targets_latest_base_version(monkeypatch) -> None:
    client = _client()
    project_id = f"proj_base_select_{uuid4().hex[:8]}"

    # Seed Node 0 context bundle required by /workflows/runs.
    r = client.post(
        "/api/v1/projects/",
        json={
            "project_id": project_id,
            "topic_title": "Editorial target selection",
            "core_idea": "Pick base, not latest variant.",
            "user_content": None,
            "target_audience": "builders",
            "content_depth": "surface",
            "tone_preference": "professional",
            "distribution_targets": ["linkedin"],
        },
    )
    assert r.status_code == 200

    # Existing versions: latest overall is variant(v2), latest base is v1.
    _seed_version(project_id, version_number=1, version_kind="base", content="# Base")
    _seed_version(
        project_id,
        version_number=2,
        version_kind="variant",
        variant_label="Balanced (50/50) - Problem/Solution",
        content="# Variant",
    )

    captured: dict[str, int] = {}

    def _fake_run_default_flow(self: OrchestrationEngine, payload) -> tuple[str, str]:
        return "run_stub", "completed"

    def _fake_run_editorial(self: OrchestrationEngine, payload):
        captured["current_version"] = payload.current_version
        return EditorialResponse(draft_version=999, updated_master_document="# Edited", change_log=["stub"])

    monkeypatch.setattr(OrchestrationEngine, "run_default_flow", _fake_run_default_flow)
    monkeypatch.setattr(OrchestrationEngine, "run_editorial", _fake_run_editorial)

    r = client.post("/api/v1/workflows/runs", json={"project_id": project_id, "run_editorial": True})
    assert r.status_code == 200
    assert r.json()["status"] == "completed_with_editorial"
    assert captured["current_version"] == 1


def test_editorial_uses_global_next_version_number() -> None:
    client = _client()
    project_id = f"proj_editorial_next_{uuid4().hex[:8]}"

    # Project row required by FK.
    r = client.post(
        "/api/v1/projects/",
        json={
            "project_id": project_id,
            "topic_title": "Editorial sequencing",
            "core_idea": "Editorial should always append globally.",
            "user_content": None,
            "target_audience": "builders",
            "content_depth": "surface",
            "tone_preference": "professional",
            "distribution_targets": ["linkedin"],
        },
    )
    assert r.status_code == 200

    # Seed two rows so editing v1 must produce v3 (not current+1 if already higher rows exist).
    _seed_version(project_id, version_number=1, version_kind="base", content="# Base v1")
    _seed_version(
        project_id,
        version_number=2,
        version_kind="variant",
        variant_label="Research-led authority (30/70) - Framework-first",
        content="# Variant v2",
    )

    r = client.post(
        "/api/v1/workflows/nodes/editorial",
        json={
            "project_id": project_id,
            "current_version": 1,
            "editor_actions": [{"action": "rewrite", "target_section": "document"}],
            "user_feedback": "Tighten flow and clarity.",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["draft_version"] == 3

    latest_list = client.get(f"/api/v1/versions/{project_id}")
    assert latest_list.status_code == 200
    versions = latest_list.json()["versions"]
    assert len(versions) >= 1
    assert versions[-1]["version_number"] == 3
    assert versions[-1]["version_kind"] == "editorial"
