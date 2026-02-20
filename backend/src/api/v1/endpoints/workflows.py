from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import EditorialRequest, EditorialResponse, MasterContentResponse, ResearchTrendResponse, TopicInitializationRequest
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.schemas.workflow import (
    ArtifactGenerateRequest,
    EditorialDraftResponse,
    EditorialDirectFinalizeRequest,
    EditorialDirectFinalizeResponse,
    EditorialFeedbackPreviewRequest,
    EditorialFeedbackPreviewResponse,
    EditorialFinalizeSelectedRequest,
    EditorialFinalizeSelectedResponse,
    EditorialRegenerateOutlineRequest,
    EditorialSaveInlineRequest,
    EditorialSessionFinalizeResponse,
    EditorialSessionIterateRequest,
    EditorialSessionIterateResponse,
    EditorialSessionStartRequest,
    EditorialSessionStartResponse,
    MasterNodeRunRequest,
    ResearchNodeRunRequest,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from src.services.orchestration.contracts import NodeExecutionContext
from src.services.orchestration.engine import OrchestrationEngine
from src.utils.ids import new_id

router = APIRouter()


def _normalize_target_audience(value):
    if isinstance(value, dict) and value.get("primary_segment"):
        return {
            "primary_segment": str(value.get("primary_segment")),
            "notes": (str(value.get("notes")).strip() if value.get("notes") is not None else None),
        }
    if isinstance(value, str) and value.strip():
        return {"primary_segment": "general", "notes": value.strip()}
    return {"primary_segment": "general", "notes": None}


def _context_bundle_from_topic(req: TopicInitializationRequest) -> dict:
    return {
        "topic_title": req.topic_title,
        "normalized_topic": req.topic_title.lower(),
        "core_idea": req.core_idea,
        "user_content": req.user_content,
        "target_audience": _normalize_target_audience(req.target_audience.model_dump()),
        "audience_familiarity": req.audience_familiarity,
        "detail_level": req.detail_level,
        "tone_preference": req.tone_preference,
        "stance": req.stance,
        "primary_goal": req.primary_goal,
        "desired_action": req.desired_action,
        "voice_profile_id": req.voice_profile_id,
        "constraints": req.constraints,
        "distribution_targets": req.distribution_targets,
    }


def _load_topic_request(project_id: str, db: Session) -> TopicInitializationRequest:
    bundle = ProjectRepository(db).get_context_bundle(project_id)
    if not bundle:
        raise HTTPException(status_code=400, detail="Initialize topic (Node 0) first via POST /projects")
    voice_profile_id = bundle.get("voice_profile_id")
    if not voice_profile_id:
        raise HTTPException(status_code=400, detail="Missing required context field: voice_profile_id")
    payload = {
        "project_id": project_id,
        "topic_title": bundle.get("topic_title") or bundle.get("normalized_topic") or "",
        "core_idea": bundle.get("core_idea") or "",
        "user_content": bundle.get("user_content"),
        "target_audience": _normalize_target_audience(bundle.get("target_audience")),
        "audience_familiarity": bundle.get("audience_familiarity"),
        "detail_level": bundle.get("detail_level"),
        "tone_preference": bundle.get("tone_preference") or "professional",
        "stance": bundle.get("stance") or "balanced",
        "primary_goal": bundle.get("primary_goal"),
        "desired_action": bundle.get("desired_action"),
        "voice_profile_id": voice_profile_id,
        "constraints": bundle.get("constraints"),
        "distribution_targets": bundle.get("distribution_targets"),
    }
    return TopicInitializationRequest.model_validate(payload)


@router.post("/runs", response_model=WorkflowRunResponse)
def run_workflow(payload: WorkflowRunRequest, db: Session = Depends(get_db)) -> WorkflowRunResponse:
    req = _load_topic_request(payload.project_id, db)
    engine = OrchestrationEngine(db)
    run_id, _ = engine.run_default_flow(req)
    # Editorial is mandatory now, so workflow run always pauses after Node 2.
    return WorkflowRunResponse(run_id=run_id, status="awaiting_editorial")


@router.get("/nodes/research/{project_id}", response_model=ResearchTrendResponse)
def run_research_node(project_id: str, db: Session = Depends(get_db)) -> ResearchTrendResponse:
    req = _load_topic_request(project_id, db)
    engine = OrchestrationEngine(db)
    ctx = NodeExecutionContext(
        project_id=project_id,
        run_id="node1",
        input_payload={"project_id": project_id},
        state={"context_bundle": _context_bundle_from_topic(req)},
    )
    return ResearchTrendResponse.model_validate(engine.node1.run(ctx).output_payload)


@router.post("/nodes/research", response_model=ResearchTrendResponse)
def run_research_node_post(payload: ResearchNodeRunRequest, db: Session = Depends(get_db)) -> ResearchTrendResponse:
    req = payload.topic
    engine = OrchestrationEngine(db)
    engine.projects.get_or_create(req.project_id)
    bundle = _context_bundle_from_topic(req)
    if payload.persist_context:
        engine.projects.set_context_bundle(req.project_id, bundle)
    ctx = NodeExecutionContext(
        project_id=req.project_id,
        run_id="node1_post",
        input_payload={"project_id": req.project_id},
        state={"context_bundle": bundle},
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
        state={"context_bundle": _context_bundle_from_topic(req)},
    )
    ctx.state["research"] = engine.node1.run(ctx).output_payload
    out = MasterContentResponse.model_validate(engine.node2.run(ctx).output_payload)

    repo = ContentRepository(db)
    base = repo.create_version(
        version_id=new_id("ver"),
        project_id=project_id,
        content=out.master_document,
        version_number=repo.next_version_number(project_id),
        version_kind="base",
        variant_label=None,
        keywords=out.core_arguments,
        structure_outline=out.structure_outline,
        version_stage="draft",
        source_version_number=None,
    )
    for mv in out.master_variants or []:
        variant_doc = (mv.master_document or "").strip()
        if not variant_doc:
            continue
        repo.create_version(
            version_id=new_id("ver"),
            project_id=project_id,
            content=variant_doc,
            version_number=repo.next_version_number(project_id),
            version_kind="variant",
            variant_label=(mv.label or "").strip() or None,
            keywords=mv.core_arguments,
            structure_outline=mv.structure_outline,
            version_stage="draft",
            source_version_number=base.version_number,
        )
    return out


@router.post("/nodes/master", response_model=MasterContentResponse)
def run_master_node_post(payload: MasterNodeRunRequest, db: Session = Depends(get_db)) -> MasterContentResponse:
    req = payload.topic
    engine = OrchestrationEngine(db)
    engine.projects.get_or_create(req.project_id)
    bundle = _context_bundle_from_topic(req)
    if payload.persist_context:
        engine.projects.set_context_bundle(req.project_id, bundle)

    ctx = NodeExecutionContext(
        project_id=req.project_id,
        run_id="node2_post",
        input_payload={"project_id": req.project_id},
        state={"context_bundle": bundle},
    )
    ctx.state["research"] = (
        payload.research.model_dump()
        if payload.research is not None
        else ResearchTrendResponse.model_validate(engine.node1.run(ctx).output_payload).model_dump()
    )

    out = MasterContentResponse.model_validate(engine.node2.run(ctx).output_payload)
    if payload.persist_versions:
        repo = ContentRepository(db)
        base = repo.create_version(
            version_id=new_id("ver"),
            project_id=req.project_id,
            content=out.master_document,
            version_number=repo.next_version_number(req.project_id),
            version_kind="base",
            variant_label=None,
            keywords=out.core_arguments,
            structure_outline=out.structure_outline,
            version_stage="draft",
            source_version_number=None,
        )
        for mv in out.master_variants or []:
            variant_doc = (mv.master_document or "").strip()
            if not variant_doc:
                continue
            repo.create_version(
                version_id=new_id("ver"),
                project_id=req.project_id,
                content=variant_doc,
                version_number=repo.next_version_number(req.project_id),
                version_kind="variant",
                variant_label=(mv.label or "").strip() or None,
                keywords=mv.core_arguments,
                structure_outline=mv.structure_outline,
                version_stage="draft",
                source_version_number=base.version_number,
            )
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


@router.post("/nodes/editorial/finalize-direct", response_model=EditorialDirectFinalizeResponse)
def finalize_editorial_direct(
    payload: EditorialDirectFinalizeRequest,
    db: Session = Depends(get_db),
) -> EditorialDirectFinalizeResponse:
    engine = OrchestrationEngine(db)
    try:
        res = engine.finalize_version_direct(project_id=payload.project_id, current_version=payload.current_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EditorialDirectFinalizeResponse(
        final_version=res.draft_version,
        final_content=res.updated_master_document,
        status="editorial_finalized",
    )


@router.post("/nodes/artifacts/generate", response_model=WorkflowRunResponse)
def generate_artifacts_for_latest_editorial(payload: ArtifactGenerateRequest, db: Session = Depends(get_db)) -> WorkflowRunResponse:
    engine = OrchestrationEngine(db)
    try:
        engine.generate_artifacts_from_latest_editorial(payload.project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkflowRunResponse(run_id=new_id("run"), status="artifacts_generated")


@router.post("/nodes/editorial/regenerate-outline", response_model=EditorialDraftResponse)
def editorial_regenerate_outline(
    payload: EditorialRegenerateOutlineRequest,
    db: Session = Depends(get_db),
) -> EditorialDraftResponse:
    engine = OrchestrationEngine(db)
    try:
        out = engine.regenerate_outline_draft(
            project_id=payload.project_id,
            source_version=payload.source_version,
            structure_outline=payload.structure_outline,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EditorialDraftResponse.model_validate(out)


@router.post("/nodes/editorial/save-inline", response_model=EditorialDraftResponse)
def editorial_save_inline(
    payload: EditorialSaveInlineRequest,
    db: Session = Depends(get_db),
) -> EditorialDraftResponse:
    engine = OrchestrationEngine(db)
    try:
        out = engine.save_inline_draft(
            project_id=payload.project_id,
            source_version=payload.source_version,
            content=payload.content,
            version_label=payload.version_label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EditorialDraftResponse.model_validate(out)


@router.post("/nodes/editorial/feedback/preview", response_model=EditorialFeedbackPreviewResponse)
def editorial_feedback_preview(
    payload: EditorialFeedbackPreviewRequest,
    db: Session = Depends(get_db),
) -> EditorialFeedbackPreviewResponse:
    engine = OrchestrationEngine(db)
    try:
        out = engine.feedback_preview(
            project_id=payload.project_id,
            source_version=payload.source_version,
            user_feedback=payload.user_feedback,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EditorialFeedbackPreviewResponse.model_validate(out)


@router.post("/nodes/editorial/finalize-selected", response_model=EditorialFinalizeSelectedResponse)
def editorial_finalize_selected(
    payload: EditorialFinalizeSelectedRequest,
    db: Session = Depends(get_db),
) -> EditorialFinalizeSelectedResponse:
    engine = OrchestrationEngine(db)
    try:
        out = engine.finalize_selected_version(project_id=payload.project_id, selected_version=payload.selected_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EditorialFinalizeSelectedResponse.model_validate(out)
