from __future__ import annotations

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
    ) -> ContentVersion:
        v = ContentVersion(
            version_id=version_id,
            project_id=project_id,
            version_number=version_number,
            version_kind=version_kind,
            variant_label=variant_label,
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
