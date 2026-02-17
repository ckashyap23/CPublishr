from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.artifact import Artifact


class ArtifactRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_artifact(
        self,
        *,
        artifact_id: str,
        project_id: str,
        artifact_type: str,
        title: str,
        content: str,
        metadata: dict | None = None,
    ) -> Artifact:
        artifact = Artifact(
            artifact_id=artifact_id,
            project_id=project_id,
            artifact_type=artifact_type,
            title=title,
            content=content,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def list_artifacts(self, project_id: str) -> list[Artifact]:
        stmt = select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.created_at.asc())
        return list(self.db.execute(stmt).scalars().all())

    def list_artifacts_by_type(self, project_id: str, artifact_type: str) -> list[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.project_id == project_id)
            .where(Artifact.artifact_type == artifact_type)
            .order_by(Artifact.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def delete_artifacts_for_project(self, project_id: str) -> int:
        rows = self.db.query(Artifact).filter(Artifact.project_id == project_id).delete(synchronize_session=False)
        self.db.commit()
        return int(rows or 0)
