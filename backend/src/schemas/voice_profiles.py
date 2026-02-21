from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceProfileCollectionCreateRequest(BaseModel):
    voice_profile_name: str = Field(min_length=1, max_length=200)
    platforms: list[str] = Field(min_length=1)


class DatasetGenerateInput(BaseModel):
    dataset_id: str | None = None
    dataset_name: str = Field(min_length=1, max_length=300)
    source_profile: str | None = None
    blob_prefix: str = Field(min_length=1, max_length=500)
    sample_scope_note: str | None = None


class VoiceProfileGenerateRequest(BaseModel):
    intended_use: str | None = None
    datasets: list[DatasetGenerateInput] = Field(min_length=1)


class VersionStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=32)


class VoiceProfileVersionSummary(BaseModel):
    voice_profile_version_id: str
    version_no: int
    is_active: bool
    generation_status: str
    intended_use: str | None = None
    core_voice: str | None = None
    approved_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class VoiceProfileCollectionEntity(BaseModel):
    voice_profile_id: str
    user_id: str
    voice_profile_name: str
    platforms: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    latest_version: VoiceProfileVersionSummary | None = None
    active_version: VoiceProfileVersionSummary | None = None


class VoiceProfileCollectionDetailResponse(BaseModel):
    collection: VoiceProfileCollectionEntity
    versions: list[VoiceProfileVersionSummary] = Field(default_factory=list)


class VoiceProfileCollectionListResponse(BaseModel):
    collections: list[VoiceProfileCollectionEntity] = Field(default_factory=list)


class VoiceProfileVersionDatasetEntity(BaseModel):
    voice_profile_version_dataset_id: str
    voice_profile_version_id: str
    dataset_id: str
    dataset_name: str | None = None
    source_profile: str | None = None
    sample_size: int | None = None
    sample_scope_note: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DatasetEntryEntity(BaseModel):
    entry_id: str
    dataset_id: str
    blob_uri: str | None = None
    source_url: str | None = None
    date_month_year: str | None = None
    text_clean: str | None = None
    reactions: int | None = None
    comments: int | None = None
    total_visible: int | None = None
    metadata_asset: str | None = None
    entry_type: str
    format_family: str | None = None
    hook_type: str | None = None
    cta_type: str | None = None
    cta_present: bool | None = None
    theme_tags: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class VoiceProfileVersionDetailResponse(BaseModel):
    version: VoiceProfileVersionSummary
    raw_profile_json: dict = Field(default_factory=dict)
    style_summary: dict = Field(default_factory=dict)
    tone_baseline: dict = Field(default_factory=dict)
    do_rules: list[str] = Field(default_factory=list)
    dont_rules: list[str] = Field(default_factory=list)
    datasets: list[VoiceProfileVersionDatasetEntity] = Field(default_factory=list)


class VoiceProfileGenerateResponse(BaseModel):
    collection: VoiceProfileCollectionEntity
    generated_version: VoiceProfileVersionDetailResponse
    dataset_entries_written: int
