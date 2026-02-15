from pydantic import BaseModel, Field


class WorkflowRunRequest(BaseModel):
    project_id: str = Field(min_length=1)
    run_editorial: bool = True
    editorial_comment: str | None = None


class WorkflowRunResponse(BaseModel):
    run_id: str
    status: str


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
