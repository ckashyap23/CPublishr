from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models.content_version import ContentVersion
from src.db.models.platform_output import PlatformOutput


class ContentRepository:
    def __init__(self, db: Session):
        self.db = db

    def next_version_number(self, project_id: str) -> int:
        stmt = select(func.max(ContentVersion.version_number)).where(ContentVersion.project_id == project_id)
        current = self.db.execute(stmt).scalar_one_or_none()
        return int(current or 0) + 1

    def create_version(
        self,
        *,
        version_id: str,
        project_id: str,
        content: str,
        version_number: int,
        version_kind: str = "base",
        variant_label: str | None = None,
        keywords: list[str] | None = None,
        structure_outline: list[str] | None = None,
        version_stage: str = "draft",
        source_version_number: int | None = None,
    ) -> ContentVersion:
        v = ContentVersion(
            version_id=version_id,
            project_id=project_id,
            version_number=version_number,
            version_kind=version_kind,
            variant_label=variant_label,
            keywords_json=json.dumps(keywords or [], ensure_ascii=False),
            structure_outline_json=json.dumps(structure_outline or [], ensure_ascii=False),
            version_stage=version_stage,
            source_version_number=source_version_number,
            updated_at=datetime.utcnow(),
            content=content,
        )
        self.db.add(v)
        self.db.commit()
        self.db.refresh(v)
        return v

    def list_versions(self, project_id: str) -> list[ContentVersion]:
        stmt = select(ContentVersion).where(ContentVersion.project_id == project_id).order_by(ContentVersion.version_number.asc())
        return list(self.db.execute(stmt).scalars().all())

    def list_versions_by_kind(self, project_id: str, version_kind: str) -> list[ContentVersion]:
        stmt = (
            select(ContentVersion)
            .where(ContentVersion.project_id == project_id)
            .where(ContentVersion.version_kind == version_kind)
            .order_by(ContentVersion.version_number.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_version_by_number(self, project_id: str, version_number: int) -> ContentVersion | None:
        stmt = (
            select(ContentVersion)
            .where(ContentVersion.project_id == project_id)
            .where(ContentVersion.version_number == version_number)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_latest_version(self, project_id: str) -> ContentVersion | None:
        stmt = (
            select(ContentVersion)
            .where(ContentVersion.project_id == project_id)
            .order_by(ContentVersion.version_number.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_latest_version_by_kind(self, project_id: str, version_kind: str) -> ContentVersion | None:
        stmt = (
            select(ContentVersion)
            .where(ContentVersion.project_id == project_id)
            .where(ContentVersion.version_kind == version_kind)
            .order_by(ContentVersion.version_number.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_latest_final_version(self, project_id: str) -> ContentVersion | None:
        stmt = (
            select(ContentVersion)
            .where(ContentVersion.project_id == project_id)
            .where(ContentVersion.version_stage == "final")
            .order_by(ContentVersion.version_number.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def update_keywords(self, project_id: str, version_number: int, keywords: list[str]) -> ContentVersion | None:
        row = self.get_version_by_number(project_id, version_number)
        if row is None:
            return None
        row.keywords_json = json.dumps(keywords or [], ensure_ascii=False)
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_structure_outline(self, project_id: str, version_number: int, structure_outline: list[str]) -> ContentVersion | None:
        row = self.get_version_by_number(project_id, version_number)
        if row is None:
            return None
        row.structure_outline_json = json.dumps(structure_outline or [], ensure_ascii=False)
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def set_version_stage(self, project_id: str, version_number: int, version_stage: str) -> ContentVersion | None:
        row = self.get_version_by_number(project_id, version_number)
        if row is None:
            return None
        row.version_stage = version_stage
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def clear_final_stage(self, project_id: str) -> int:
        rows = (
            self.db.query(ContentVersion)
            .filter(ContentVersion.project_id == project_id)
            .filter(ContentVersion.version_stage == "final")
            .all()
        )
        for row in rows:
            row.version_stage = "draft"
            row.updated_at = datetime.utcnow()
            self.db.add(row)
        self.db.commit()
        return len(rows)

    @staticmethod
    def decode_keywords(row: ContentVersion) -> list[str]:
        try:
            data = json.loads(row.keywords_json or "[]")
            if isinstance(data, list):
                return [str(x) for x in data]
        except json.JSONDecodeError:
            pass
        return []

    @staticmethod
    def decode_structure_outline(row: ContentVersion) -> list[str]:
        try:
            data = json.loads(row.structure_outline_json or "[]")
            if isinstance(data, list):
                return [str(x) for x in data]
        except json.JSONDecodeError:
            pass
        return []

    def create_platform_output(
        self,
        *,
        output_id: str,
        project_id: str,
        platform: str,
        format_type: str,
        content: str,
        optimized: bool,
    ) -> PlatformOutput:
        o = PlatformOutput(
            output_id=output_id,
            project_id=project_id,
            platform=platform,
            format_type=format_type,
            content=content,
            optimized=optimized,
        )
        self.db.add(o)
        self.db.commit()
        self.db.refresh(o)
        return o

    def list_platform_outputs(self, project_id: str) -> list[PlatformOutput]:
        stmt = select(PlatformOutput).where(PlatformOutput.project_id == project_id).order_by(PlatformOutput.platform.asc())
        return list(self.db.execute(stmt).scalars().all())

    def get_latest_platform_output(self, project_id: str, platform: str) -> PlatformOutput | None:
        stmt = (
            select(PlatformOutput)
            .where(PlatformOutput.project_id == project_id)
            .where(PlatformOutput.platform == platform)
            .order_by(PlatformOutput.output_id.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def delete_platform_outputs_for_project(self, project_id: str) -> int:
        rows = self.db.query(PlatformOutput).filter(PlatformOutput.project_id == project_id).delete()
        self.db.commit()
        return int(rows or 0)

