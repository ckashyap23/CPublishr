from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class EditorialSession(Base):
    __tablename__ = "editorial_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    base_version: Mapped[int] = mapped_column(Integer, nullable=False)
    current_iteration: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    working_content: Mapped[str] = mapped_column(Text, nullable=False)
    finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
