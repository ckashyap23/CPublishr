from pydantic import BaseModel, Field

from src.contracts.prd import ArtifactEntity, ArtifactFormat


class ArtifactGenerationRequest(BaseModel):
    project_id: str
    requested_formats: list[ArtifactFormat] = Field(default_factory=list)
    revision_mode: str = "new_revision"
    style_settings: dict = Field(default_factory=dict)
    style_settings_by_format: dict[str, dict] = Field(default_factory=dict)


class ArtifactGenerationResponse(BaseModel):
    project_id: str
    requested_formats: list[str]
    options: dict
    artifacts: list[ArtifactEntity]
