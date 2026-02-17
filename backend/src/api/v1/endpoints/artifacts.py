import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import ArtifactEntity, ArtifactListResponse, ArtifactType
from src.db.repositories.artifact_repository import ArtifactRepository

router = APIRouter()


@router.get("/{project_id}", response_model=ArtifactListResponse)
def list_artifacts(project_id: str, db: Session = Depends(get_db)) -> ArtifactListResponse:
    rows = ArtifactRepository(db).list_artifacts(project_id)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[
            ArtifactEntity(
                artifact_id=a.artifact_id,
                project_id=a.project_id,
                artifact_type=a.artifact_type,
                title=a.title,
                content=a.content,
                metadata=(json.loads(a.metadata_json or "{}") if a.metadata_json else {}),
            )
            for a in rows
        ],
    )


@router.get("/{project_id}/{artifact_type}", response_model=ArtifactListResponse)
def list_artifacts_by_type(
    project_id: str,
    artifact_type: ArtifactType,
    db: Session = Depends(get_db),
) -> ArtifactListResponse:
    rows = ArtifactRepository(db).list_artifacts_by_type(project_id, artifact_type)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[
            ArtifactEntity(
                artifact_id=a.artifact_id,
                project_id=a.project_id,
                artifact_type=a.artifact_type,
                title=a.title,
                content=a.content,
                metadata=(json.loads(a.metadata_json or "{}") if a.metadata_json else {}),
            )
            for a in rows
        ],
    )
