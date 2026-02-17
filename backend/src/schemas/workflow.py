from pydantic import BaseModel, Field

from src.contracts.prd import ResearchTrendResponse, TopicInitializationRequest


class WorkflowRunRequest(BaseModel):
    project_id: str = Field(min_length=1)


class WorkflowRunResponse(BaseModel):
    run_id: str
    status: str


class ResearchNodeRunRequest(BaseModel):
    topic: TopicInitializationRequest
    persist_context: bool = True


class MasterNodeRunRequest(BaseModel):
    topic: TopicInitializationRequest
    research: ResearchTrendResponse | None = None
    persist_context: bool = True
    persist_versions: bool = True


class EditorialSessionStartRequest(BaseModel):
    project_id: str
    current_version: int
    user_comment: str


class EditorialSessionStartResponse(BaseModel):
    session_id: str
    iteration: int
    preview_content: str
    change_log: list[str]


class EditorialSessionIterateRequest(BaseModel):
    user_comment: str


class EditorialSessionIterateResponse(BaseModel):
    session_id: str
    iteration: int
    preview_content: str
    change_log: list[str]


class EditorialSessionFinalizeResponse(BaseModel):
    session_id: str
    final_version: int
    final_content: str


class EditorialDirectFinalizeRequest(BaseModel):
    project_id: str
    current_version: int


class EditorialDirectFinalizeResponse(BaseModel):
    final_version: int
    final_content: str
    status: str


class ArtifactGenerateRequest(BaseModel):
    project_id: str


class VersionKeywordsPatchRequest(BaseModel):
    keywords: list[str] = Field(default_factory=list)


class VersionKeywordsPatchResponse(BaseModel):
    project_id: str
    version_number: int
    keywords: list[str]
    updated: bool


class EditorialRegenerateOutlineRequest(BaseModel):
    project_id: str
    source_version: int
    structure_outline: list[str] = Field(default_factory=list)


class EditorialSaveInlineRequest(BaseModel):
    project_id: str
    source_version: int
    content: str
    version_label: str | None = None


class EditorialDraftResponse(BaseModel):
    project_id: str
    source_version: int
    draft_version: int
    content: str
    version_kind: str
    variant_label: str | None = None
    version_stage: str = "draft"


class EditorialFeedbackPreviewRequest(BaseModel):
    project_id: str
    source_version: int
    user_feedback: str


class EditorialFeedbackPreviewResponse(BaseModel):
    project_id: str
    source_version: int
    preview_content: str
    change_log: list[str] = Field(default_factory=list)


class EditorialFinalizeSelectedRequest(BaseModel):
    project_id: str
    selected_version: int


class EditorialFinalizeSelectedResponse(BaseModel):
    project_id: str
    final_version: int
    status: str
