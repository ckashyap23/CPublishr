from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class VoiceProfileVersion(Base):
    __tablename__ = "voice_profile_versions"
    __table_args__ = (
        UniqueConstraint("voice_profile_id", "version_no", name="uq_voice_profile_versions_profile_version_no"),
    )

    voice_profile_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    voice_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voice_profile_collections.voice_profile_id"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    intended_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tone_baseline: Mapped[dict] = mapped_column(JSONB, nullable=False)
    do_rules: Mapped[list] = mapped_column(JSONB, nullable=False)
    dont_rules: Mapped[list] = mapped_column(JSONB, nullable=False)
    raw_profile_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generation_status: Mapped[str] = mapped_column(Text, nullable=False, default="generated")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
