from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.contracts.prd import ContentVersionEntity, ContentVersionKind, ContentVersionListResponse
from src.db.repositories.content_repository import ContentRepository

router = APIRouter()


@router.get("/{project_id}", response_model=ContentVersionListResponse)
def list_versions(project_id: str, db: Session = Depends(get_db)) -> ContentVersionListResponse:
    versions = ContentRepository(db).list_versions(project_id)
    return ContentVersionListResponse(
        project_id=project_id,
        versions=[
            ContentVersionEntity(
                version_id=v.version_id,
                project_id=v.project_id,
                version_number=v.version_number,
                version_kind=v.version_kind,
                variant_label=v.variant_label,
                content=v.content,
            )
            for v in versions
        ],
    )


@router.get("/{project_id}/{version_kind}", response_model=ContentVersionListResponse)
def list_versions_by_kind(
    project_id: str,
    version_kind: ContentVersionKind,
    db: Session = Depends(get_db),
) -> ContentVersionListResponse:
    versions = ContentRepository(db).list_versions_by_kind(project_id, version_kind)
    return ContentVersionListResponse(
        project_id=project_id,
        versions=[
            ContentVersionEntity(
                version_id=v.version_id,
                project_id=v.project_id,
                version_number=v.version_number,
                version_kind=v.version_kind,
                variant_label=v.variant_label,
                content=v.content,
            )
            for v in versions
        ],
    )
