from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from src.db.init_db import create_all
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.editorial_session_repository import EditorialSessionRepository
from src.db.repositories.publish_repository import PublishRepository
from src.db.session import SessionLocal, get_engine, init_engine
from src.main import app
from src.utils.ids import new_id


def _client() -> TestClient:
    init_engine()
    engine = get_engine()
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


def test_project_initialize_resets_project_scoped_tables() -> None:
    client = _client()
    headers, voice_profile_id, user_id = _auth(client)
    project_id = f"proj_reset_{uuid4().hex[:8]}"
    payload = {
        "project_id": project_id,
        "topic_title": "Reset behavior",
        "core_idea": "Node 0 starts fresh",
        "user_content": None,
        "target_audience": {"primary_segment": "builders_developers", "notes": None},
        "detail_level": "quick_take",
        "tone_preference": "professional",
        "voice_profile_id": voice_profile_id,
        "distribution_targets": ["linkedin"],
    }

    # First init creates project/context.
    r = client.post("/api/v1/projects/", json=payload, headers=headers)
    assert r.status_code == 200

    # Seed project-scoped rows to verify they are removed on re-init.
    with SessionLocal() as db:
        content_repo = ContentRepository(db, user_id=user_id)
        publish_repo = PublishRepository(db, user_id=user_id)
        editorial_repo = EditorialSessionRepository(db, user_id=user_id)

        content_repo.create_version(
            version_id=new_id("ver"),
            project_id=project_id,
            content="# seeded",
            version_number=1,
            version_kind="base",
            variant_label=None,
        )
        content_repo.create_platform_output(
            output_id=new_id("out"),
            project_id=project_id,
            platform="linkedin",
            format_type="default",
            content='{"linkedin_post":{"body":"seed"}}',
            optimized=True,
        )
        publish_repo.create_job(
            publish_job_id=new_id("pub"),
            project_id=project_id,
            platform="linkedin",
            payload_snapshot={"project_id": project_id},
        )
        editorial_repo.create(
            session_id=new_id("edit"),
            project_id=project_id,
            base_version=1,
            working_content="# working",
        )

    # Re-init should wipe old project-scoped rows.
    r = client.post("/api/v1/projects/", json=payload, headers=headers)
    assert r.status_code == 200

    versions = client.get(f"/api/v1/versions/{project_id}", headers=headers).json()["versions"]
    outputs = client.get(f"/api/v1/platform-outputs/{project_id}", headers=headers).json()["outputs"]
    assert versions == []
    assert outputs == []

    with SessionLocal() as db:
        jobs = PublishRepository(db, user_id=user_id).list_jobs_for_project(project_id)
        assert jobs == []
