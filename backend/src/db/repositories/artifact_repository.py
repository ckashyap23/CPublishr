from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.artifact import Artifact
from src.services.orchestration.artifact_schema import derive_kind


class ArtifactRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create_artifact(
        self,
        *,
        artifact_id: str,
        project_id: str,
        format: str,
        title: str | None = None,
        payload_json: dict | None = None,
        tags_json: list[str] | None = None,
        status: str = "generated",
        revision: int = 1,
        parent_artifact_id: str | None = None,
    ) -> Artifact:
        resolved_kind = derive_kind(format)
        artifact = Artifact(
            artifact_id=artifact_id,
            user_id=self.user_id,
            project_id=project_id,
            format=format,
            kind=resolved_kind,
            title=title,
            payload_json=payload_json or {},
            tags_json=tags_json or [],
            status=status,
            revision=int(revision or 1),
            parent_artifact_id=parent_artifact_id,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def list_artifacts(self, project_id: str) -> list[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.user_id == self.user_id)
            .where(Artifact.project_id == project_id)
            .order_by(Artifact.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_artifacts_by_format(self, project_id: str, format: str) -> list[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.user_id == self.user_id)
            .where(Artifact.project_id == project_id)
            .where(Artifact.format == format)
            .order_by(Artifact.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_artifacts_by_kind(self, project_id: str, kind: str) -> list[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.user_id == self.user_id)
            .where(Artifact.project_id == project_id)
            .where(Artifact.kind == kind)
            .order_by(Artifact.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_latest_by_format(self, project_id: str, format: str) -> Artifact | None:
        stmt = (
            select(Artifact)
            .where(Artifact.user_id == self.user_id)
            .where(Artifact.project_id == project_id)
            .where(Artifact.format == format)
            .order_by(Artifact.revision.desc(), Artifact.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        stmt = (
            select(Artifact)
            .where(Artifact.user_id == self.user_id)
            .where(Artifact.artifact_id == artifact_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    @staticmethod
    def _artifact_has_blob_path(row: Artifact, blob_path: str) -> bool:
        payload = row.payload_json if isinstance(row.payload_json, dict) else {}
        assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
        needle = str(blob_path or "").strip()
        if not needle:
            return False
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            candidate = str(asset.get("blob_path") or "").strip()
            if candidate and candidate == needle:
                return True
        return False

    def find_artifact_by_blob_path(self, *, project_id: str, blob_path: str) -> Artifact | None:
        needle = str(blob_path or "").strip()
        if not needle:
            return None
        for row in self.list_artifacts(project_id):
            if self._artifact_has_blob_path(row, needle):
                return row
        return None

    def find_artifacts_by_blob_paths(self, *, project_id: str, blob_paths: list[str]) -> list[Artifact]:
        wanted = {str(path or "").strip() for path in blob_paths if str(path or "").strip()}
        if not wanted:
            return []
        matched: list[Artifact] = []
        for row in self.list_artifacts(project_id):
            for path in wanted:
                if self._artifact_has_blob_path(row, path):
                    matched.append(row)
                    break
        return matched

    def update_title(self, artifact_id: str, title: str | None) -> Artifact | None:
        row = self.get_artifact(artifact_id)
        if row is None:
            return None
        row.title = title
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_artifact(
        self,
        artifact_id: str,
        *,
        title: str | None = None,
        payload_json: dict | None = None,
        tags_json: list[str] | None = None,
        status: str | None = None,
    ) -> Artifact | None:
        row = self.get_artifact(artifact_id)
        if row is None:
            return None
        if title is not None:
            row.title = title
        if payload_json is not None:
            row.payload_json = payload_json
        if tags_json is not None:
            row.tags_json = tags_json
        if status is not None:
            row.status = status
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def lineage(self, artifact_id: str) -> list[Artifact]:
        rows: list[Artifact] = []
        current = self.db.get(Artifact, artifact_id)
        while current is not None:
            rows.append(current)
            parent_id = current.parent_artifact_id
            if not parent_id:
                break
            current = self.db.get(Artifact, parent_id)
        rows.reverse()
        return rows

    def create_next_revision(
        self,
        *,
        project_id: str,
        format: str,
        artifact_id: str,
        title: str | None = None,
        payload_json: dict | None = None,
        tags_json: list[str] | None = None,
        status: str = "generated",
    ) -> Artifact:
        latest = self.get_latest_by_format(project_id, format)
        next_revision = int((latest.revision if latest else 0) + 1)
        parent_id = latest.artifact_id if latest else None
        return self.create_artifact(
            artifact_id=artifact_id,
            project_id=project_id,
            format=format,
            title=title,
            payload_json=payload_json,
            tags_json=tags_json,
            status=status,
            revision=next_revision,
            parent_artifact_id=parent_id,
        )

    def delete_artifacts_for_project(self, project_id: str) -> int:
        rows = (
            self.db.query(Artifact)
            .filter(Artifact.user_id == self.user_id)
            .filter(Artifact.project_id == project_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return int(rows or 0)
