from __future__ import annotations

from datetime import datetime
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.publish_job import PublishJob


class PublishRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create_job(
        self,
        *,
        publish_job_id: str,
        project_id: str,
        platform: str,
        status: str = "published",
        scheduled_time: datetime | None = None,
        external_id: str | None = None,
        platform_output_id: str | None = None,
        payload_snapshot: dict | None = None,
    ) -> PublishJob:
        job = PublishJob(
            publish_job_id=publish_job_id,
            user_id=self.user_id,
            project_id=project_id,
            platform=platform,
            status=status,
            scheduled_time=scheduled_time,
            external_id=external_id,
            platform_output_id=platform_output_id,
            payload_snapshot=json.dumps(payload_snapshot or {}, ensure_ascii=False),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs_for_project(self, project_id: str, limit: int = 50) -> list[PublishJob]:
        stmt = (
            select(PublishJob)
            .where(PublishJob.user_id == self.user_id)
            .where(PublishJob.project_id == project_id)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())







