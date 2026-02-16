from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.project import Project
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
