from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.artifact import Artifact
from src.db.models.content_version import ContentVersion
from src.db.models.editorial_session import EditorialSession
from src.db.models.platform_output import PlatformOutput
from src.db.models.project import Project
from src.db.models.publish_job import PublishJob
from src.schemas.context_bundle import ContextBundleV1


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, project_id: str) -> Project | None:
        return self.db.get(Project, project_id)

    def get_or_create(self, project_id: str, *, status: str = "draft") -> Project:
        p = self.get(project_id)
        if p is not None:
            return p
        p = Project(project_id=project_id, status=status)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def reset_project_data(self, project_id: str) -> dict[str, int]:
        deleted_versions = (
            self.db.query(ContentVersion)
            .filter(ContentVersion.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_outputs = (
            self.db.query(PlatformOutput)
            .filter(PlatformOutput.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_jobs = (
            self.db.query(PublishJob)
            .filter(PublishJob.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_sessions = (
            self.db.query(EditorialSession)
            .filter(EditorialSession.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_artifacts = (
            self.db.query(Artifact)
            .filter(Artifact.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_project_rows = (
            self.db.query(Project)
            .filter(Project.project_id == project_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return {
            "content_versions": int(deleted_versions or 0),
            "platform_outputs": int(deleted_outputs or 0),
            "publish_jobs": int(deleted_jobs or 0),
            "editorial_sessions": int(deleted_sessions or 0),
            "artifacts": int(deleted_artifacts or 0),
            "projects": int(deleted_project_rows or 0),
        }

    def set_context_bundle(self, project_id: str, context_bundle: dict) -> Project:
        p = self.get_or_create(project_id)
        # Validate the bundle shape before persisting (allowing extra keys).
        ContextBundleV1.model_validate(context_bundle or {})
        p.context_json = json.dumps(context_bundle or {}, ensure_ascii=False)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def get_context_bundle(self, project_id: str) -> dict | None:
        p = self.get(project_id)
        if p is None:
            return None
        try:
            return json.loads(p.context_json or "{}")
        except json.JSONDecodeError:
            return None

    def list_projects(self, limit: int = 50) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def set_final_version(self, project_id: str, final_version_number: int) -> Project:
        p = self.get_or_create(project_id)
        p.final_version_number = int(final_version_number)
        p.finalized_at = datetime.utcnow()
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p
