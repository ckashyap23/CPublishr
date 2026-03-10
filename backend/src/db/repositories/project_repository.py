from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models.artifact import Artifact
from src.db.models.content_version import ContentVersion
from src.db.models.editorial_session import EditorialSession
from src.db.models.platform_output import PlatformOutput
from src.db.models.project import Project
from src.db.models.publish_job import PublishJob
from src.schemas.context_bundle import ContextBundleV1


class ProjectRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def get(self, project_id: str) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.user_id == self.user_id)
            .where(Project.project_id == project_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_or_create(self, project_id: str, *, status: str = "draft") -> Project:
        p = self.get(project_id)
        if p is not None:
            return p
        p = Project(project_id=project_id, user_id=self.user_id, status=status)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def reset_project_data(self, project_id: str) -> dict[str, int]:
        deleted_versions = (
            self.db.query(ContentVersion)
            .filter(ContentVersion.user_id == self.user_id)
            .filter(ContentVersion.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_outputs = (
            self.db.query(PlatformOutput)
            .filter(PlatformOutput.user_id == self.user_id)
            .filter(PlatformOutput.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_jobs = (
            self.db.query(PublishJob)
            .filter(PublishJob.user_id == self.user_id)
            .filter(PublishJob.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_sessions = (
            self.db.query(EditorialSession)
            .filter(EditorialSession.user_id == self.user_id)
            .filter(EditorialSession.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_artifacts = (
            self.db.query(Artifact)
            .filter(Artifact.user_id == self.user_id)
            .filter(Artifact.project_id == project_id)
            .delete(synchronize_session=False)
        )
        deleted_project_rows = (
            self.db.query(Project)
            .filter(Project.user_id == self.user_id)
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

    def _ensure_projects_from_activity(self) -> None:
        """Backfill missing project rows from user-scoped activity tables."""
        existing_ids = set(
            self.db.execute(
                select(Project.project_id).where(Project.user_id == self.user_id)
            ).scalars().all()
        )
        candidate_ids: set[str] = set()
        for model in (ContentVersion, PlatformOutput, PublishJob, EditorialSession, Artifact):
            ids = self.db.execute(
                select(model.project_id).where(model.user_id == self.user_id).distinct()
            ).scalars().all()
            for pid in ids:
                value = str(pid or "").strip()
                if value:
                    candidate_ids.add(value)

        missing = sorted(candidate_ids - existing_ids)
        if not missing:
            return

        for pid in missing:
            self.db.add(Project(project_id=pid, user_id=self.user_id, status="draft"))
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

    def list_projects(self, limit: int | None = None) -> list[Project]:
        self._ensure_projects_from_activity()
        stmt = (
            select(Project)
            .where(Project.user_id == self.user_id)
            .order_by(Project.created_at.desc())
        )
        if isinstance(limit, int) and limit > 0:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def set_final_version(self, project_id: str, final_version_number: int) -> Project:
        p = self.get_or_create(project_id)
        p.final_version_number = int(final_version_number)
        p.finalized_at = datetime.utcnow()
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p
