from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import EditorialRequest, EditorialResponse, MasterContentResponse, ResearchTrendResponse, TopicInitializationRequest
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.schemas.workflow import (
    EditorialSessionFinalizeResponse,
    EditorialSessionIterateRequest,
    EditorialSessionIterateResponse,
    EditorialSessionStartRequest,
    EditorialSessionStartResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from src.services.orchestration.contracts import NodeExecutionContext
from src.services.orchestration.engine import OrchestrationEngine
from src.utils.ids import new_id

router = APIRouter()


def _load_topic_request(project_id: str, db: Session) -> TopicInitializationRequest:
    bundle = ProjectRepository(db).get_context_bundle(project_id)
    if not bundle:
        raise HTTPException(status_code=400, detail="Initialize topic (Node 0) first via POST /projects")
    payload = {
        "project_id": project_id,
        "topic_title": bundle.get("topic_title") or bundle.get("normalized_topic") or "",
        "core_idea": bundle.get("core_idea") or "",
        "target_audience": bundle.get("target_audience") or "builders",
        "content_depth": bundle.get("content_depth") or "intermediate",
        "tone_preference": bundle.get("tone_preference") or "professional",
        "distribution_targets": bundle.get("distribution_targets") or [],
    }
    return TopicInitializationRequest.model_validate(payload)


@router.post("/runs", response_model=WorkflowRunResponse)
def run_workflow(payload: WorkflowRunRequest, db: Session = Depends(get_db)) -> WorkflowRunResponse:
    req = _load_topic_request(payload.project_id, db)
    engine = OrchestrationEngine(db)
    run_id, status = engine.run_default_flow(req)

    if payload.run_editorial:
        latest = ContentRepository(db).get_latest_version(payload.project_id)
        if latest is not None:
            engine.run_editorial(
                EditorialRequest(
                    project_id=payload.project_id,
                    current_version=latest.version_number,
                    editor_actions=[{"action": "rewrite", "target_section": "document"}],
                    user_feedback=payload.editorial_comment or "Polish and improve clarity for publishing.",
                )
            )
            status = "completed_with_editorial"
    return WorkflowRunResponse(run_id=run_id, status=status)


@router.get("/nodes/research/{project_id}", response_model=ResearchTrendResponse)
def run_research_node(project_id: str, db: Session = Depends(get_db)) -> ResearchTrendResponse:
    req = _load_topic_request(project_id, db)
    engine = OrchestrationEngine(db)
    ctx = NodeExecutionContext(
        project_id=project_id,
        run_id="node1",
        input_payload={"project_id": project_id},
        state={"context_bundle": {
            "topic_title": req.topic_title,
            "normalized_topic": req.topic_title.lower(),
            "core_idea": req.core_idea,
            "target_audience": req.target_audience,
            "content_depth": req.content_depth,
            "tone_preference": req.tone_preference,
            "distribution_targets": req.distribution_targets,
        }},
    )
    return ResearchTrendResponse.model_validate(engine.node1.run(ctx).output_payload)


@router.get("/nodes/master/{project_id}", response_model=MasterContentResponse)
def run_master_node(project_id: str, db: Session = Depends(get_db)) -> MasterContentResponse:
    req = _load_topic_request(project_id, db)
    engine = OrchestrationEngine(db)
    ctx = NodeExecutionContext(
        project_id=project_id,
        run_id="node2",
        input_payload={"project_id": project_id},
        state={"context_bundle": {
            "topic_title": req.topic_title,
            "normalized_topic": req.topic_title.lower(),
            "core_idea": req.core_idea,
            "target_audience": req.target_audience,
            "content_depth": req.content_depth,
            "tone_preference": req.tone_preference,
            "distribution_targets": req.distribution_targets,
        }},
    )
    ctx.state["research"] = engine.node1.run(ctx).output_payload
    out = MasterContentResponse.model_validate(engine.node2.run(ctx).output_payload)

    repo = ContentRepository(db)
    repo.create_version(version_id=new_id("ver"), project_id=project_id, content=out.master_document, version_number=repo.next_version_number(project_id))
    return out


@router.post("/nodes/editorial", response_model=EditorialResponse)
def run_editorial_node(payload: EditorialRequest, db: Session = Depends(get_db)) -> EditorialResponse:
    try:
        return OrchestrationEngine(db).run_editorial(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/nodes/editorial/session/start", response_model=EditorialSessionStartResponse)
def start_editorial_session(payload: EditorialSessionStartRequest, db: Session = Depends(get_db)) -> EditorialSessionStartResponse:
    engine = OrchestrationEngine(db)
    try:
        session_id, res, iteration = engine.start_editorial_session(
            project_id=payload.project_id,
            current_version=payload.current_version,
            user_comment=payload.user_comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return EditorialSessionStartResponse(
        session_id=session_id,
        iteration=iteration,
        preview_content=res.updated_master_document,
        change_log=res.change_log,
    )


@router.post("/nodes/editorial/session/{session_id}/iterate", response_model=EditorialSessionIterateResponse)
def iterate_editorial_session(
    session_id: str,
    payload: EditorialSessionIterateRequest,
    db: Session = Depends(get_db),
) -> EditorialSessionIterateResponse:
    engine = OrchestrationEngine(db)
    try:
        res, iteration = engine.iterate_editorial_session(session_id=session_id, user_comment=payload.user_comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return EditorialSessionIterateResponse(
        session_id=session_id,
        iteration=iteration,
        preview_content=res.updated_master_document,
        change_log=res.change_log,
    )


@router.post("/nodes/editorial/session/{session_id}/finalize", response_model=EditorialSessionFinalizeResponse)
def finalize_editorial_session(session_id: str, db: Session = Depends(get_db)) -> EditorialSessionFinalizeResponse:
    engine = OrchestrationEngine(db)
    try:
        res = engine.finalize_editorial_session(session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return EditorialSessionFinalizeResponse(
        session_id=session_id,
        final_version=res.draft_version,
        final_content=res.updated_master_document,
    )
