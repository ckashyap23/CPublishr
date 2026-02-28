from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.contracts.prd import DistributionRequest, DistributionResponse
from src.schemas.publishing_schemas import (
    ArtifactPublishJobResponse,
    ArtifactPublishRequest,
    OutputPathPickRequest,
    OutputPathPickResponse,
    PublishPlatformFieldSchemaResponse,
    PublishPlatformListResponse,
    OutputPathBrowseResponse,
    SaveToPublishRequest,
    SaveToPublishResponse,
)
from src.services.publishing.service import PublishingService

router = APIRouter()


@router.get("/platforms", response_model=PublishPlatformListResponse)
def list_publish_platforms(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PublishPlatformListResponse:
    return PublishPlatformListResponse(platforms=PublishingService(db, user_id=user_id).list_available_platforms())


@router.get("/platforms/{platform}/fields", response_model=PublishPlatformFieldSchemaResponse)
def get_publish_platform_fields(
    platform: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PublishPlatformFieldSchemaResponse:
    try:
        data = PublishingService(db, user_id=user_id).get_platform_field_schema(platform)
        return PublishPlatformFieldSchemaResponse.model_validate(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs", response_model=DistributionResponse)
def create_publish_job(
    payload: DistributionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DistributionResponse:
    try:
        return PublishingService(db, user_id=user_id).create_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/artifacts", response_model=ArtifactPublishJobResponse)
def create_artifact_publish_job(
    payload: ArtifactPublishRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactPublishJobResponse:
    try:
        return PublishingService(db, user_id=user_id).create_artifact_publish_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/save-to-publish", response_model=SaveToPublishResponse)
def save_to_publish(
    payload: SaveToPublishRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SaveToPublishResponse:
    try:
        return PublishingService(db, user_id=user_id).save_to_publish(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/output-path/browse", response_model=OutputPathBrowseResponse)
def browse_output_path(
    path: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> OutputPathBrowseResponse:
    try:
        data = PublishingService(db, user_id=user_id).browse_output_locations(path)
        return OutputPathBrowseResponse.model_validate(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/output-path/pick-local", response_model=OutputPathPickResponse)
def pick_local_output_path(
    payload: OutputPathPickRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> OutputPathPickResponse:
    try:
        selected = PublishingService(db, user_id=user_id).pick_local_output_path(payload.start_path)
        return OutputPathPickResponse(selected_path=selected)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
