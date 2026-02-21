from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        CheckConstraint("kind IN ('text','image','video','audio','gif','bundle')", name="ck_artifacts_kind"),
    )

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    format: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tags_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="generated", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
