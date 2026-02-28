from __future__ import annotations

from pydantic import BaseModel, Field


class PublishFieldArtifactSource(BaseModel):
    artifact_id: str
    part: str
    render_as: str | None = None
    order: int | None = None


class PublishFieldArtifactMapping(BaseModel):
    field_key: str
    sources: list[PublishFieldArtifactSource] = Field(default_factory=list)


class ArtifactPublishRequest(BaseModel):
    project_id: str
    platform: str
    field_mappings: list[PublishFieldArtifactMapping] = Field(default_factory=list)
    scheduled_time: str | None = None


class PublishPlatformFieldSchemaResponse(BaseModel):
    platform: str
    fields: list[dict] = Field(default_factory=list)


class PublishPlatformListResponse(BaseModel):
    platforms: list[str] = Field(default_factory=list)


class ArtifactPublishJobResponse(BaseModel):
    publish_job_id: str
    project_id: str
    platform: str
    status: str
    external_id: str | None = None
    external_url: str | None = None
    scheduled_time: str | None = None
    payload_snapshot: dict = Field(default_factory=dict)


class SaveToPublishRequest(BaseModel):
    project_id: str
    platform: str
    user_name: str
    output_path: str | None = None
    field_mappings: list[PublishFieldArtifactMapping] = Field(default_factory=list)


class SaveToPublishResponse(BaseModel):
    status: str = "saved"
    project_id: str
    platform: str
    user_name: str
    output_path: str


class OutputPathBrowseResponse(BaseModel):
    current_path: str
    parent_path: str | None = None
    directories: list[str] = Field(default_factory=list)


class OutputPathPickRequest(BaseModel):
    start_path: str | None = None


class OutputPathPickResponse(BaseModel):
    selected_path: str | None = None
