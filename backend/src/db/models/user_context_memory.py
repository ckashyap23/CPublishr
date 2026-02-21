from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class UserContextMemory(Base):
    __tablename__ = "user_context_memory"

    memory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    last_project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_view: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
