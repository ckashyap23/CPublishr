from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    final_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
