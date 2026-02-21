from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from src.db.init_db import create_all
from src.db.repositories.content_repository import ContentRepository
from src.db.session import SessionLocal, get_engine, init_engine
from src.main import app
from src.utils.ids import new_id


def _client() -> TestClient:
    init_engine()
    engine = get_engine()
    assert "sqlite" not in str(engine.url), "Tests must run against DATABASE_URL from .env (Postgres)"
    create_all(engine)
    return TestClient(app)


def _auth(client: TestClient) -> tuple[dict[str, str], str, str]:
    slug = uuid4().hex[:10]
    email = f"tester_{slug}@example.com"
    res = client.post(
        "/api/v1/auth/signup",
        json={"user_id": f"usr_{slug}", "email": email, "password": "Passw0rd123"},
    )
    assert res.status_code == 200
    data = res.json()
    token = data["access_token"]
    user_id = data["user"]["user_id"]
    return {"Authorization": f"Bearer {token}"}, data["default_voice_profile_id"], user_id


def _seed_version(
    project_id: str,
    user_id: str,
    *,
    version_number: int,
    version_kind: str,
    content: str,
    variant_label: str | None = None,
) -> None:
    with SessionLocal() as db:
        repo = ContentRepository(db, user_id=user_id)
        repo.create_version(
            version_id=new_id("ver"),
            project_id=project_id,
            content=content,
            version_number=version_number,
            version_kind=version_kind,
            variant_label=variant_label,
        )


def test_workflow_run_status_is_awaiting_editorial() -> None:
    client = _client()
    headers, voice_profile_id, user_id = _auth(client)
    project_id = f"proj_base_select_{uuid4().hex[:8]}"

    # Seed Node 0 context bundle required by /workflows/runs.
    r = client.post(
        "/api/v1/projects/",
        json={
            "project_id": project_id,
            "topic_title": "Editorial target selection",
            "core_idea": "Pick base, not latest variant.",
            "user_content": None,
            "target_audience": {"primary_segment": "builders_developers", "notes": None},
            "detail_level": "quick_take",
            "tone_preference": "professional",
            "voice_profile_id": voice_profile_id,
            "distribution_targets": ["linkedin"],
        },
        headers=headers,
    )
    assert r.status_code == 200

    # Existing versions: latest overall is variant(v2), latest base is v1.
    _seed_version(project_id, user_id=user_id, version_number=1, version_kind="base", content="# Base")
    _seed_version(
        project_id,
        user_id=user_id,
        version_number=2,
        version_kind="variant",
        variant_label="Balanced (50/50) - Problem/Solution",
        content="# Variant",
    )

    r = client.post("/api/v1/workflows/runs", json={"project_id": project_id}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_editorial"


def test_editorial_uses_global_next_version_number() -> None:
    client = _client()
    headers, voice_profile_id, user_id = _auth(client)
    project_id = f"proj_editorial_next_{uuid4().hex[:8]}"

    # Project row required by FK.
    r = client.post(
        "/api/v1/projects/",
        json={
            "project_id": project_id,
            "topic_title": "Editorial sequencing",
            "core_idea": "Editorial should always append globally.",
            "user_content": None,
            "target_audience": {"primary_segment": "builders_developers", "notes": None},
            "detail_level": "quick_take",
            "tone_preference": "professional",
            "voice_profile_id": voice_profile_id,
            "distribution_targets": ["linkedin"],
        },
        headers=headers,
    )
    assert r.status_code == 200

    # Seed two rows so editing v1 must produce v3 (not current+1 if already higher rows exist).
    _seed_version(project_id, user_id=user_id, version_number=1, version_kind="base", content="# Base v1")
    _seed_version(
        project_id,
        user_id=user_id,
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
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["draft_version"] == 3

    latest_list = client.get(f"/api/v1/versions/{project_id}", headers=headers)
    assert latest_list.status_code == 200
    versions = latest_list.json()["versions"]
    assert len(versions) >= 1
    assert versions[-1]["version_number"] == 3
    assert versions[-1]["version_kind"] == "editorial"


def test_editorial_session_finalize_carries_variant_label_for_variant_source() -> None:
    client = _client()
    headers, voice_profile_id, user_id = _auth(client)
    project_id = f"proj_editorial_session_variant_{uuid4().hex[:8]}"

    r = client.post(
        "/api/v1/projects/",
        json={
            "project_id": project_id,
            "topic_title": "Editorial session lineage",
            "core_idea": "Finalize should carry variant label when source is variant.",
            "user_content": None,
            "target_audience": {"primary_segment": "builders_developers", "notes": None},
            "detail_level": "quick_take",
            "tone_preference": "professional",
            "voice_profile_id": voice_profile_id,
            "distribution_targets": ["linkedin"],
        },
        headers=headers,
    )
    assert r.status_code == 200

    variant_label = "Balanced (50/50) - Problem/Solution"
    _seed_version(project_id, user_id=user_id, version_number=1, version_kind="base", content="# Base v1")
    _seed_version(
        project_id,
        user_id=user_id,
        version_number=2,
        version_kind="variant",
        variant_label=variant_label,
        content="# Variant v2",
    )

    # Start session from variant version_number=2.
    r = client.post(
        "/api/v1/workflows/nodes/editorial/session/start",
        json={
            "project_id": project_id,
            "current_version": 2,
            "user_comment": "Tighten this variant for publishing.",
        },
        headers=headers,
    )
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    # Finalize session and verify persisted editorial row carries source variant_label.
    r = client.post(f"/api/v1/workflows/nodes/editorial/session/{session_id}/finalize", headers=headers)
    assert r.status_code == 200
    final_version = r.json()["final_version"]

    with SessionLocal() as db:
        persisted = ContentRepository(db, user_id=user_id).get_version_by_number(project_id, int(final_version))
        assert persisted is not None
        assert persisted.version_kind == "editorial"
        assert persisted.variant_label == variant_label


def test_editorial_direct_finalize_generates_artifacts_and_carries_variant_label() -> None:
    client = _client()
    headers, voice_profile_id, user_id = _auth(client)
    project_id = f"proj_editorial_direct_{uuid4().hex[:8]}"

    r = client.post(
        "/api/v1/projects/",
        json={
            "project_id": project_id,
            "topic_title": "Editorial direct finalize",
            "core_idea": "Direct finalize without iterations.",
            "user_content": None,
            "target_audience": {"primary_segment": "builders_developers", "notes": None},
            "detail_level": "quick_take",
            "tone_preference": "professional",
            "voice_profile_id": voice_profile_id,
            "distribution_targets": ["linkedin"],
        },
        headers=headers,
    )
    assert r.status_code == 200

    variant_label = "Balanced (50/50) - Problem/Solution"
    _seed_version(project_id, user_id=user_id, version_number=1, version_kind="base", content="# Base v1")
    _seed_version(
        project_id,
        user_id=user_id,
        version_number=2,
        version_kind="variant",
        variant_label=variant_label,
        content="# Variant v2",
    )

    r = client.post(
        "/api/v1/workflows/nodes/editorial/finalize-direct",
        json={"project_id": project_id, "current_version": 2},
        headers=headers,
    )
    assert r.status_code == 200
    final_version = r.json()["final_version"]

    with SessionLocal() as db:
        persisted = ContentRepository(db, user_id=user_id).get_version_by_number(project_id, int(final_version))
        assert persisted is not None
        assert persisted.version_kind == "editorial"
        assert persisted.variant_label == variant_label

    artifacts = client.get(f"/api/v1/artifacts/{project_id}", headers=headers)
    assert artifacts.status_code == 200
    rows = artifacts.json()["artifacts"]
    assert len(rows) >= 1
