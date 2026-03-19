from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models.dataset_entry import DatasetEntry
from src.db.models.voice_profile import VoiceProfile
from src.db.models.voice_profile_collection import VoiceProfileCollection
from src.db.models.voice_profile_dataset import VoiceProfileDataset
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

    def get_collection(self, collection_id: uuid.UUID) -> VoiceProfileCollection | None:
        stmt = (
            select(VoiceProfileCollection)
            .where(VoiceProfileCollection.user_id == self.user_id)
            .where(VoiceProfileCollection.collection_id == collection_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create_collection(self, *, collection_name: str, platforms: list[str]) -> VoiceProfileCollection:
        now = datetime.now(UTC)
        collection = VoiceProfileCollection(
            collection_id=uuid.uuid4(),
            user_id=self.user_id,
            collection_name=collection_name.strip(),
            platforms=sorted({str(x).strip().lower() for x in platforms if str(x).strip()}),
            created_at=now,
            updated_at=now,
        )
        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)
        return collection

    def list_datasets(self, collection_id: uuid.UUID) -> list[VoiceProfileDataset]:
        stmt = (
            select(VoiceProfileDataset)
            .where(VoiceProfileDataset.user_id == self.user_id)
            .where(VoiceProfileDataset.collection_id == collection_id)
            .order_by(VoiceProfileDataset.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_dataset(self, dataset_id: uuid.UUID) -> VoiceProfileDataset | None:
        stmt = (
            select(VoiceProfileDataset)
            .where(VoiceProfileDataset.user_id == self.user_id)
            .where(VoiceProfileDataset.dataset_id == dataset_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create_dataset(
        self,
        *,
        collection_id: uuid.UUID,
        dataset_name: str,
        source_profile: str | None,
        blob_prefix: str,
        sample_scope_note: str | None,
    ) -> VoiceProfileDataset:
        now = datetime.now(UTC)
        row = VoiceProfileDataset(
            dataset_id=uuid.uuid4(),
            collection_id=collection_id,
            user_id=self.user_id,
            dataset_name=dataset_name.strip(),
            source_profile=source_profile,
            blob_prefix=blob_prefix.strip(),
            sample_scope_note=sample_scope_note,
            entry_count=0,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def update_dataset_entry_count(self, dataset_id: uuid.UUID, entry_count: int) -> VoiceProfileDataset:
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("Dataset not found")
        dataset.entry_count = int(entry_count)
        dataset.updated_at = datetime.now(UTC)
        self.db.add(dataset)
        return dataset

    def list_voice_profiles(self, collection_id: uuid.UUID | None = None) -> list[VoiceProfile]:
        stmt = select(VoiceProfile).where(VoiceProfile.user_id == self.user_id)
        if collection_id is not None:
            stmt = stmt.where(VoiceProfile.collection_id == collection_id)
        stmt = stmt.order_by(VoiceProfile.updated_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_voice_profile(self, voice_profile_id: uuid.UUID) -> VoiceProfile | None:
        stmt = (
            select(VoiceProfile)
            .where(VoiceProfile.user_id == self.user_id)
            .where(VoiceProfile.voice_profile_id == voice_profile_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create_voice_profile(self, *, collection_id: uuid.UUID, voice_profile_name: str) -> VoiceProfile:
        now = datetime.now(UTC)
        row = VoiceProfile(
            voice_profile_id=uuid.uuid4(),
            collection_id=collection_id,
            user_id=self.user_id,
            voice_profile_name=voice_profile_name.strip(),
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def set_voice_profile_enabled(self, voice_profile_id: uuid.UUID, is_enabled: bool) -> VoiceProfile:
        row = self.get_voice_profile(voice_profile_id)
        if row is None:
            raise ValueError("Voice profile not found")
        row.is_enabled = bool(is_enabled)
        row.updated_at = datetime.now(UTC)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_voice_profile(self, voice_profile_id: uuid.UUID) -> None:
        row = self.get_voice_profile(voice_profile_id)
        if row is None:
            raise ValueError("Voice profile not found")
        versions = self.list_versions(voice_profile_id)
        for version in versions:
            self.db.query(VoiceProfileVersionDataset).filter(
                VoiceProfileVersionDataset.voice_profile_version_id == version.voice_profile_version_id
            ).delete(synchronize_session=False)
        self.db.query(VoiceProfileVersion).filter(
            VoiceProfileVersion.voice_profile_id == voice_profile_id
        ).delete(synchronize_session=False)
        self.db.delete(row)
        self.db.commit()

    def list_versions(self, voice_profile_id: uuid.UUID) -> list[VoiceProfileVersion]:
        stmt = (
            select(VoiceProfileVersion)
            .join(VoiceProfile, VoiceProfile.voice_profile_id == VoiceProfileVersion.voice_profile_id)
            .where(VoiceProfile.user_id == self.user_id)
            .where(VoiceProfileVersion.voice_profile_id == voice_profile_id)
            .order_by(VoiceProfileVersion.version_no.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_version(self, voice_profile_version_id: uuid.UUID) -> VoiceProfileVersion | None:
        stmt = (
            select(VoiceProfileVersion)
            .join(VoiceProfile, VoiceProfile.voice_profile_id == VoiceProfileVersion.voice_profile_id)
            .where(VoiceProfile.user_id == self.user_id)
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

    def add_version_dataset(
        self,
        *,
        voice_profile_version_id: uuid.UUID,
        dataset: VoiceProfileDataset,
        sample_size: int | None,
    ) -> VoiceProfileVersionDataset:
        now = datetime.now(UTC)
        row = VoiceProfileVersionDataset(
            voice_profile_version_dataset_id=uuid.uuid4(),
            voice_profile_version_id=voice_profile_version_id,
            dataset_id=dataset.dataset_id,
            dataset_name=dataset.dataset_name,
            source_profile=dataset.source_profile,
            sample_size=sample_size,
            sample_scope_note=dataset.sample_scope_note,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        return row

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
            .join(VoiceProfileDataset, VoiceProfileDataset.dataset_id == DatasetEntry.dataset_id)
            .where(VoiceProfileDataset.user_id == self.user_id)
            .where(DatasetEntry.dataset_id == dataset_id)
            .order_by(DatasetEntry.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_version_datasets(self, voice_profile_version_id: uuid.UUID) -> list[VoiceProfileVersionDataset]:
        stmt = (
            select(VoiceProfileVersionDataset)
            .join(VoiceProfileVersion, VoiceProfileVersion.voice_profile_version_id == VoiceProfileVersionDataset.voice_profile_version_id)
            .join(VoiceProfile, VoiceProfile.voice_profile_id == VoiceProfileVersion.voice_profile_id)
            .where(VoiceProfile.user_id == self.user_id)
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
