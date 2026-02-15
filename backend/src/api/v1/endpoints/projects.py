from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import ProjectEntity, TopicInitializationRequest, TopicInitializationResponse
from src.db.repositories.project_repository import ProjectRepository
from src.services.orchestration.contracts import NodeExecutionContext
from src.services.orchestration.engine import OrchestrationEngine
from src.utils.time import to_utc_iso

router = APIRouter()


@router.post("/", response_model=TopicInitializationResponse)
def initialize_topic(payload: TopicInitializationRequest, db: Session = Depends(get_db)) -> TopicInitializationResponse:
    engine = OrchestrationEngine(db)
    engine.projects.get_or_create(payload.project_id)
    ctx = NodeExecutionContext(project_id=payload.project_id, run_id="node0", input_payload=payload.model_dump())
    res = engine.node0.run(ctx)
    validated = TopicInitializationResponse.model_validate(res.output_payload)
    engine.projects.set_context_bundle(payload.project_id, validated.context_bundle)
    return validated


@router.get("/{project_id}", response_model=ProjectEntity)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectEntity:
    project = ProjectRepository(db).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectEntity(project_id=project.project_id, status=project.status, created_at=to_utc_iso(project.created_at))
