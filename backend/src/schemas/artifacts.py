from typing import Literal

from pydantic import BaseModel, Field

from src.contracts.prd import ArtifactEntity, ArtifactFormat


class ArtifactGenerationRequest(BaseModel):
    project_id: str
    requested_formats: list[ArtifactFormat] = Field(default_factory=list)
    revision_mode: str = "new_revision"
    style_settings_by_kind: dict[str, dict] = Field(default_factory=dict)
    style_settings_by_format: dict[str, dict] = Field(default_factory=dict)


class ArtifactGenerationResponse(BaseModel):
    project_id: str
    requested_formats: list[str]
    options: dict
    artifacts: list[ArtifactEntity]
    generation_errors: list[dict] = Field(default_factory=list)


class ArtifactTitleUpdateRequest(BaseModel):
    title: str | None = None


class ArtifactEditRequest(BaseModel):
    artifact_id: str
    mode: Literal["inline", "iterate"]
    inline_content: str | None = None
    edit_instruction: str | None = None
    style_settings_by_kind: dict[str, dict] = Field(default_factory=dict)
    style_settings_by_format: dict[str, dict] = Field(default_factory=dict)
    source_blob_paths: list[str] = Field(default_factory=list)


class ArtifactEditResponse(BaseModel):
    status: str
    artifact: ArtifactEntity | None = None
    detail: str | None = None


class ArtifactSuggestRequest(BaseModel):
    project_id: str
    formats: list[str] = Field(default_factory=list)


class ArtifactSuggestResponse(BaseModel):
    suggestions: dict[str, dict] = Field(default_factory=dict)
