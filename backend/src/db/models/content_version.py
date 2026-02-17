from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ContentVersion(Base):
    __tablename__ = "content_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_kind: Mapped[str] = mapped_column(String(32), default="base", nullable=False)
    variant_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keywords_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    structure_outline_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    version_stage: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    source_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
