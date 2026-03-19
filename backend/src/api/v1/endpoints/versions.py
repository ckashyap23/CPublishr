from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.contracts.prd import ContentVersionEntity, ContentVersionKind, ContentVersionListResponse
from src.db.models.content_version import ContentVersion
from src.db.repositories.content_repository import ContentRepository
from src.schemas.workflow import VersionKeywordsPatchRequest, VersionKeywordsPatchResponse
from src.utils.time import to_utc_iso

router = APIRouter()


def _to_content_version_entity(repo: ContentRepository, v: ContentVersion) -> ContentVersionEntity:
    return ContentVersionEntity(
        version_id=v.version_id,
        project_id=v.project_id,
        version_number=v.version_number,
        version_kind=v.version_kind,
        variant_label=v.variant_label,
        keywords=repo.decode_keywords(v),
        structure_outline=repo.decode_structure_outline(v),
        version_stage=v.version_stage,
        source_version_number=v.source_version_number,
        updated_at=to_utc_iso(v.updated_at) if v.updated_at else None,
        content=v.content,
    )


@router.get("/{project_id}", response_model=ContentVersionListResponse)
def list_versions(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ContentVersionListResponse:
    repo = ContentRepository(db, user_id=user_id)
    versions = repo.list_versions(project_id)
    return ContentVersionListResponse(
        project_id=project_id,
        versions=[_to_content_version_entity(repo, v) for v in versions],
    )


@router.get("/{project_id}/{version_kind}", response_model=ContentVersionListResponse)
def list_versions_by_kind(
    project_id: str,
    version_kind: ContentVersionKind,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ContentVersionListResponse:
    repo = ContentRepository(db, user_id=user_id)
    versions = repo.list_versions_by_kind(project_id, version_kind)
    return ContentVersionListResponse(
        project_id=project_id,
        versions=[_to_content_version_entity(repo, v) for v in versions],
    )


@router.patch("/{project_id}/{version_number}/keywords", response_model=VersionKeywordsPatchResponse)
def patch_version_keywords(
    project_id: str,
    version_number: int,
    payload: VersionKeywordsPatchRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VersionKeywordsPatchResponse:
    repo = ContentRepository(db, user_id=user_id)
    updated = repo.update_keywords(project_id, version_number, payload.keywords)
    if updated is None:
        raise HTTPException(status_code=404, detail="Content version not found")
    return VersionKeywordsPatchResponse(
        project_id=project_id,
        version_number=version_number,
        keywords=repo.decode_keywords(updated),
        updated=True,
    )
