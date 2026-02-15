from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PlatformOutput(Base):
    __tablename__ = "platform_outputs"

    output_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    format_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    optimized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
