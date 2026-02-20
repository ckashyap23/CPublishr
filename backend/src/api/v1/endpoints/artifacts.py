import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import ArtifactEntity, ArtifactFormat, ArtifactKind, ArtifactListResponse
from src.db.repositories.artifact_repository import ArtifactRepository
from src.schemas.artifacts import ArtifactGenerationRequest, ArtifactGenerationResponse
from src.services.orchestration.artifacts.contracts import GenerationOptions
from src.services.orchestration.artifacts.orchestrator import ArtifactPipelineOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_entity(a) -> ArtifactEntity:
    return ArtifactEntity(
        artifact_id=a.artifact_id,
        project_id=a.project_id,
        format=a.format,
        kind=a.kind,
        title=a.title,
        payload_json=a.payload_json or {},
        tags_json=a.tags_json or [],
        status=a.status,
        revision=a.revision,
        parent_artifact_id=a.parent_artifact_id,
        created_at=(a.created_at.isoformat() if a.created_at else None),
        updated_at=(a.updated_at.isoformat() if a.updated_at else None),
    )


@router.post("/generate", response_model=ArtifactGenerationResponse)
def generate_artifacts(payload: ArtifactGenerationRequest, db: Session = Depends(get_db)) -> ArtifactGenerationResponse:
    orchestrator = ArtifactPipelineOrchestrator(db)
    requested_formats = payload.requested_formats or []
    try:
        out = orchestrator.generate(
            project_id=payload.project_id,
            requested_formats=[str(x) for x in requested_formats],
            options=GenerationOptions(
                revision_mode=payload.revision_mode,
            ),
            style_settings=payload.style_settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Artifact generation failed for project_id=%s", payload.project_id)
        raise HTTPException(status_code=500, detail=f"Artifact generation failed: {exc}") from exc
    return ArtifactGenerationResponse.model_validate(out)


@router.get("/catalog/formats")
def artifact_formats_catalog() -> dict:
    from src.services.orchestration.artifact_schema import formats_by_kind_map

    return {"formats_by_kind": formats_by_kind_map()}


@router.get("/{project_id}", response_model=ArtifactListResponse)
def list_artifacts(project_id: str, db: Session = Depends(get_db)) -> ArtifactListResponse:
    rows = ArtifactRepository(db).list_artifacts(project_id)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[_to_entity(a) for a in rows],
    )


@router.get("/{project_id}/{format}", response_model=ArtifactListResponse)
def list_artifacts_by_format(
    project_id: str,
    format: ArtifactFormat,
    db: Session = Depends(get_db),
) -> ArtifactListResponse:
    rows = ArtifactRepository(db).list_artifacts_by_format(project_id, format)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[_to_entity(a) for a in rows],
    )


@router.get("/{project_id}/kind/{kind}", response_model=ArtifactListResponse)
def list_artifacts_by_kind(
    project_id: str,
    kind: ArtifactKind,
    db: Session = Depends(get_db),
) -> ArtifactListResponse:
    rows = ArtifactRepository(db).list_artifacts_by_kind(project_id, kind)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[_to_entity(a) for a in rows],
    )
