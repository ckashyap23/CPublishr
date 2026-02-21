from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class DatasetEntry(Base):
    __tablename__ = "dataset_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('text_post','carousel','image_post','video','reel','short_video','podcast_clip','thread','email','blog_post','other')",
            name="ck_dataset_entries_entry_type",
        ),
    )

    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    blob_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_month_year: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_clean: Mapped[str | None] = mapped_column(Text, nullable=True)
    reactions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_visible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_asset: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_type: Mapped[str] = mapped_column(Text, nullable=False)
    format_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    theme_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
