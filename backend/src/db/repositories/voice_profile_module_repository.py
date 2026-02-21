from __future__ import annotations

import uuid
from datetime import datetime, UTC

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models.dataset_entry import DatasetEntry
from src.db.models.voice_profile_collection import VoiceProfileCollection
from src.db.models.voice_profile_version import VoiceProfileVersion
from src.db.models.voice_profile_version_dataset import VoiceProfileVersionDataset


class VoiceProfileModuleRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def list_collections(self) -> list[VoiceProfileCollection]:
        stmt = (
            select(VoiceProfileCollection)
            .where(VoiceProfileCollection.user_id == self.user_id)
            .order_by(VoiceProfileCollection.updated_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_collection(self, voice_profile_id: uuid.UUID) -> VoiceProfileCollection | None:
        stmt = (
            select(VoiceProfileCollection)
            .where(VoiceProfileCollection.user_id == self.user_id)
            .where(VoiceProfileCollection.voice_profile_id == voice_profile_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create_collection(self, *, voice_profile_name: str, platforms: list[str]) -> tuple[VoiceProfileCollection, VoiceProfileVersion]:
        now = datetime.now(UTC)
        collection = VoiceProfileCollection(
            voice_profile_id=uuid.uuid4(),
            user_id=self.user_id,
            voice_profile_name=voice_profile_name.strip(),
            platforms=sorted({str(x).strip().lower() for x in platforms if str(x).strip()}),
            created_at=now,
            updated_at=now,
        )
        self.db.add(collection)
        self.db.flush()

        initial = VoiceProfileVersion(
            voice_profile_version_id=uuid.uuid4(),
            voice_profile_id=collection.voice_profile_id,
            version_no=1,
            is_active=False,
            intended_use=None,
            core_voice=None,
            style_summary={},
            tone_baseline={},
            do_rules=[],
            dont_rules=[],
            raw_profile_json={},
            generation_status="draft",
            approved_at=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(initial)
        self.db.commit()
        self.db.refresh(collection)
        self.db.refresh(initial)
        return collection, initial

    def list_versions(self, voice_profile_id: uuid.UUID) -> list[VoiceProfileVersion]:
        stmt = (
            select(VoiceProfileVersion)
            .join(VoiceProfileCollection, VoiceProfileCollection.voice_profile_id == VoiceProfileVersion.voice_profile_id)
            .where(VoiceProfileCollection.user_id == self.user_id)
            .where(VoiceProfileVersion.voice_profile_id == voice_profile_id)
            .order_by(VoiceProfileVersion.version_no.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_version(self, voice_profile_version_id: uuid.UUID) -> VoiceProfileVersion | None:
        stmt = (
            select(VoiceProfileVersion)
            .join(VoiceProfileCollection, VoiceProfileCollection.voice_profile_id == VoiceProfileVersion.voice_profile_id)
            .where(VoiceProfileCollection.user_id == self.user_id)
            .where(VoiceProfileVersion.voice_profile_version_id == voice_profile_version_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def next_version_no(self, voice_profile_id: uuid.UUID) -> int:
        stmt = select(func.max(VoiceProfileVersion.version_no)).where(VoiceProfileVersion.voice_profile_id == voice_profile_id)
        current = self.db.execute(stmt).scalar_one_or_none()
        return int(current or 0) + 1

    def create_generated_version(
        self,
        *,
        voice_profile_id: uuid.UUID,
        intended_use: str | None,
        core_voice: str | None,
        style_summary: dict,
        tone_baseline: dict,
        do_rules: list[str],
        dont_rules: list[str],
        raw_profile_json: dict,
        generation_status: str,
    ) -> VoiceProfileVersion:
        now = datetime.now(UTC)
        row = VoiceProfileVersion(
            voice_profile_version_id=uuid.uuid4(),
            voice_profile_id=voice_profile_id,
            version_no=self.next_version_no(voice_profile_id),
            is_active=False,
            intended_use=intended_use,
            core_voice=core_voice,
            style_summary=style_summary or {},
            tone_baseline=tone_baseline or {},
            do_rules=[str(x) for x in (do_rules or [])],
            dont_rules=[str(x) for x in (dont_rules or [])],
            raw_profile_json=raw_profile_json or {},
            generation_status=generation_status or "generated",
            approved_at=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def upsert_version_dataset(
        self,
        *,
        voice_profile_version_id: uuid.UUID,
        dataset_id: uuid.UUID,
        dataset_name: str | None,
        source_profile: str | None,
        sample_size: int | None,
        sample_scope_note: str | None,
    ) -> VoiceProfileVersionDataset:
        stmt = (
            select(VoiceProfileVersionDataset)
            .where(VoiceProfileVersionDataset.voice_profile_version_id == voice_profile_version_id)
            .where(VoiceProfileVersionDataset.dataset_id == dataset_id)
            .limit(1)
        )
        existing = self.db.execute(stmt).scalars().first()
        now = datetime.now(UTC)
        if existing is None:
            existing = VoiceProfileVersionDataset(
                voice_profile_version_dataset_id=uuid.uuid4(),
                voice_profile_version_id=voice_profile_version_id,
                dataset_id=dataset_id,
                dataset_name=dataset_name,
                source_profile=source_profile,
                sample_size=sample_size,
                sample_scope_note=sample_scope_note,
                created_at=now,
                updated_at=now,
            )
            self.db.add(existing)
        else:
            existing.dataset_name = dataset_name or existing.dataset_name
            existing.source_profile = source_profile or existing.source_profile
            existing.sample_size = sample_size if sample_size is not None else existing.sample_size
            existing.sample_scope_note = sample_scope_note or existing.sample_scope_note
            existing.updated_at = now
            self.db.add(existing)
        return existing

    def upsert_dataset_entry(self, **kwargs) -> DatasetEntry:
        entry_id: uuid.UUID = kwargs["entry_id"]
        stmt = select(DatasetEntry).where(DatasetEntry.entry_id == entry_id).limit(1)
        existing = self.db.execute(stmt).scalars().first()
        now = datetime.now(UTC)
        if existing is None:
            existing = DatasetEntry(created_at=now, updated_at=now, **kwargs)
            self.db.add(existing)
            return existing

        for k, v in kwargs.items():
            if v is not None:
                setattr(existing, k, v)
        existing.updated_at = now
        self.db.add(existing)
        return existing

    def list_dataset_entries(self, dataset_id: uuid.UUID) -> list[DatasetEntry]:
        stmt = (
            select(DatasetEntry)
            .where(DatasetEntry.dataset_id == dataset_id)
            .order_by(DatasetEntry.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_version_datasets(self, voice_profile_version_id: uuid.UUID) -> list[VoiceProfileVersionDataset]:
        stmt = (
            select(VoiceProfileVersionDataset)
            .where(VoiceProfileVersionDataset.voice_profile_version_id == voice_profile_version_id)
            .order_by(VoiceProfileVersionDataset.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def activate_version(self, voice_profile_version_id: uuid.UUID) -> VoiceProfileVersion:
        version = self.get_version(voice_profile_version_id)
        if version is None:
            raise ValueError("Voice profile version not found")

        rows = (
            self.db.query(VoiceProfileVersion)
            .filter(VoiceProfileVersion.voice_profile_id == version.voice_profile_id)
            .all()
        )
        now = datetime.now(UTC)
        for row in rows:
            row.is_active = row.voice_profile_version_id == voice_profile_version_id
            row.updated_at = now
            self.db.add(row)
        version.generation_status = "approved"
        version.approved_at = now
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def update_version_status(self, voice_profile_version_id: uuid.UUID, status_value: str) -> VoiceProfileVersion:
        version = self.get_version(voice_profile_version_id)
        if version is None:
            raise ValueError("Voice profile version not found")
        normalized = status_value.strip().lower()
        if normalized not in {"generated", "approved", "rejected", "draft", "failed"}:
            raise ValueError("Unsupported status")
        now = datetime.now(UTC)
        version.generation_status = normalized
        if normalized == "approved":
            version.approved_at = now
        version.updated_at = now
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def commit(self) -> None:
        self.db.commit()
