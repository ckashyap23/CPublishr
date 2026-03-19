from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class VoiceProfileDataset(Base):
    __tablename__ = "voice_profile_datasets"
    __table_args__ = (
        UniqueConstraint("collection_id", "dataset_name", name="uq_voice_profile_datasets_collection_name"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voice_profile_collections.collection_id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    blob_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    sample_scope_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
