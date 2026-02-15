from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import ContentVersionEntity, ContentVersionListResponse
from src.db.repositories.content_repository import ContentRepository

router = APIRouter()


@router.get("/{project_id}/latest", response_model=ContentVersionEntity)
def get_latest_version(project_id: str, db: Session = Depends(get_db)) -> ContentVersionEntity:
    repo = ContentRepository(db)
    latest = repo.get_latest_version(project_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="No versions found for project")
    return ContentVersionEntity(
        version_id=latest.version_id,
        project_id=latest.project_id,
        version_number=latest.version_number,
        content=latest.content,
    )


@router.get("/{project_id}", response_model=ContentVersionListResponse)
def list_versions(project_id: str, db: Session = Depends(get_db)) -> ContentVersionListResponse:
    versions = ContentRepository(db).list_versions(project_id)
    return ContentVersionListResponse(project_id=project_id, versions=[ContentVersionEntity(version_id=v.version_id, project_id=v.project_id, version_number=v.version_number, content=v.content) for v in versions])
