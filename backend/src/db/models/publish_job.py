from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PublishJob(Base):
    __tablename__ = "publish_jobs"

    publish_job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="published", nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    platform_output_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_snapshot: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
