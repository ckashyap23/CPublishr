from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceProfileCollectionCreateRequest(BaseModel):
    collection_name: str = Field(min_length=1, max_length=200)
    platforms: list[str] = Field(min_length=1)


class VoiceProfileDatasetCreateRequest(BaseModel):
    dataset_name: str = Field(min_length=1, max_length=300)
    source_profile: str | None = None
    source_type: str | None = None
    blob_prefix: str = Field(min_length=1, max_length=1000)
    sample_scope_note: str | None = None


class VoiceProfileCreateRequest(BaseModel):
    voice_profile_name: str = Field(min_length=1, max_length=200)


class VoiceProfileGenerateRequest(BaseModel):
    intended_use: str | None = None
    dataset_ids: list[str] = Field(min_length=1)


class VoiceProfileManualVersionCreateRequest(BaseModel):
    intended_use: str | None = None
    core_voice: str | None = None
    summary: str | None = None
    do_rules: list[str] = Field(default_factory=list)
    dont_rules: list[str] = Field(default_factory=list)


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
    collection_id: str
    user_id: str
    collection_name: str
    platforms: list[str] = Field(default_factory=list)
    dataset_count: int = 0
    voice_profile_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class VoiceProfileCollectionDetailResponse(BaseModel):
    collection: VoiceProfileCollectionEntity
    datasets: list["VoiceProfileDatasetEntity"] = Field(default_factory=list)
    voice_profiles: list["VoiceProfileEntity"] = Field(default_factory=list)


class VoiceProfileCollectionListResponse(BaseModel):
    collections: list[VoiceProfileCollectionEntity] = Field(default_factory=list)


class VoiceProfileDatasetEntity(BaseModel):
    dataset_id: str
    collection_id: str
    user_id: str
    dataset_name: str
    source_profile: str | None = None
    source_type: str | None = None
    blob_prefix: str
    sample_scope_note: str | None = None
    entry_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class VoiceProfileEntity(BaseModel):
    voice_profile_id: str
    collection_id: str
    user_id: str
    voice_profile_name: str
    is_enabled: bool = True
    latest_version: VoiceProfileVersionSummary | None = None
    active_version: VoiceProfileVersionSummary | None = None
    created_at: str | None = None
    updated_at: str | None = None


class VoiceProfileDetailResponse(BaseModel):
    voice_profile: VoiceProfileEntity
    versions: list[VoiceProfileVersionSummary] = Field(default_factory=list)


class VoiceProfileListResponse(BaseModel):
    voice_profiles: list[VoiceProfileEntity] = Field(default_factory=list)


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


class VoiceProfileDatasetCreateResponse(BaseModel):
    collection: VoiceProfileCollectionEntity
    dataset: VoiceProfileDatasetEntity
    dataset_entries_written: int


class VoiceProfileCreateResponse(BaseModel):
    collection: VoiceProfileCollectionEntity
    voice_profile: VoiceProfileEntity


class VoiceProfileGenerateResponse(BaseModel):
    voice_profile: VoiceProfileEntity
    generated_version: VoiceProfileVersionDetailResponse


class VoiceProfileStatusUpdateRequest(BaseModel):
    is_enabled: bool
