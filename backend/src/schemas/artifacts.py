from pydantic import BaseModel, Field

from src.contracts.prd import ArtifactEntity, ArtifactFormat


class ArtifactGenerationStages(BaseModel):
    plan: bool = True
    prompt_pack: bool = True
    render_media: bool = True
    assemble: bool = True
    package: bool = True


class ArtifactGenerationRequest(BaseModel):
    project_id: str
    requested_formats: list[ArtifactFormat] = Field(default_factory=list)
    stages: ArtifactGenerationStages = Field(default_factory=ArtifactGenerationStages)
    revision_mode: str = "new_revision"
    style_settings: dict = Field(default_factory=dict)


class ArtifactGenerationResponse(BaseModel):
    project_id: str
    requested_formats: list[str]
    stages: dict
    options: dict
    artifacts: list[ArtifactEntity]