from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.db.repositories.voice_profile_module_repository import VoiceProfileModuleRepository
from src.schemas.voice_profiles import (
    VoiceProfileCollectionCreateRequest,
    VoiceProfileCollectionDetailResponse,
    VoiceProfileCollectionEntity,
    VoiceProfileCollectionListResponse,
    VoiceProfileGenerateRequest,
    VoiceProfileGenerateResponse,
    VoiceProfileVersionDatasetEntity,
    VoiceProfileVersionDetailResponse,
    VoiceProfileVersionSummary,
    VersionStatusUpdateRequest,
)
from src.services.voice_profiles.service import VoiceProfileModuleService
from src.utils.time import to_utc_iso

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_version_summary(v) -> VoiceProfileVersionSummary:
    return VoiceProfileVersionSummary(
        voice_profile_version_id=str(v.voice_profile_version_id),
        version_no=int(v.version_no),
        is_active=bool(v.is_active),
        generation_status=v.generation_status,
        intended_use=v.intended_use,
        core_voice=v.core_voice,
        approved_at=to_utc_iso(v.approved_at) if v.approved_at else None,
        created_at=to_utc_iso(v.created_at) if v.created_at else None,
        updated_at=to_utc_iso(v.updated_at) if v.updated_at else None,
    )


def _to_collection_entity(collection, versions) -> VoiceProfileCollectionEntity:
    latest = versions[0] if versions else None
    active = next((x for x in versions if x.is_active), None)
    return VoiceProfileCollectionEntity(
        voice_profile_id=str(collection.voice_profile_id),
        user_id=collection.user_id,
        voice_profile_name=collection.voice_profile_name,
        platforms=[str(x) for x in (collection.platforms or [])],
        created_at=to_utc_iso(collection.created_at) if collection.created_at else None,
        updated_at=to_utc_iso(collection.updated_at) if collection.updated_at else None,
        latest_version=_to_version_summary(latest) if latest else None,
        active_version=_to_version_summary(active) if active else None,
    )


@router.post("/collections", response_model=VoiceProfileCollectionDetailResponse)
def create_collection(
    payload: VoiceProfileCollectionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileCollectionDetailResponse:
    svc = VoiceProfileModuleService(db, user_id=user_id)
    try:
        collection, initial = svc.create_collection(
            voice_profile_name=payload.voice_profile_name,
            platforms=payload.platforms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    entity = _to_collection_entity(collection, [initial])
    return VoiceProfileCollectionDetailResponse(collection=entity, versions=[_to_version_summary(initial)])


@router.get("/collections", response_model=VoiceProfileCollectionListResponse)
def list_collections(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileCollectionListResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    rows = repo.list_collections()
    entities = []
    for row in rows:
        versions = repo.list_versions(row.voice_profile_id)
        entities.append(_to_collection_entity(row, versions))
    return VoiceProfileCollectionListResponse(collections=entities)


@router.get("/collections/{voice_profile_id}", response_model=VoiceProfileCollectionDetailResponse)
def get_collection(
    voice_profile_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileCollectionDetailResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    try:
        profile_uuid = uuid.UUID(voice_profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid voice_profile_id") from exc
    row = repo.get_collection(profile_uuid)
    if row is None:
        raise HTTPException(status_code=404, detail="Voice profile collection not found")
    versions = repo.list_versions(profile_uuid)
    return VoiceProfileCollectionDetailResponse(
        collection=_to_collection_entity(row, versions),
        versions=[_to_version_summary(v) for v in versions],
    )


@router.post("/collections/{voice_profile_id}/versions/generate", response_model=VoiceProfileGenerateResponse)
def generate_version(
    voice_profile_id: str,
    payload: VoiceProfileGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileGenerateResponse:
    try:
        profile_uuid = uuid.UUID(voice_profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid voice_profile_id") from exc
    svc = VoiceProfileModuleService(db, user_id=user_id)
    try:
        collection, version, written = svc.generate_new_version(
            voice_profile_id=profile_uuid,
            intended_use=payload.intended_use,
            datasets=payload.datasets,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during voice profile generation")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during voice profile generation: {exc.__class__.__name__}: {str(exc)}",
        ) from exc
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    versions = repo.list_versions(profile_uuid)
    datasets = repo.list_version_datasets(version.voice_profile_version_id)
    collection_entity = _to_collection_entity(collection, versions)
    version_detail = VoiceProfileVersionDetailResponse(
        version=_to_version_summary(version),
        raw_profile_json=version.raw_profile_json or {},
        style_summary=version.style_summary or {},
        tone_baseline=version.tone_baseline or {},
        do_rules=[str(x) for x in (version.do_rules or [])],
        dont_rules=[str(x) for x in (version.dont_rules or [])],
        datasets=[
            VoiceProfileVersionDatasetEntity(
                voice_profile_version_dataset_id=str(d.voice_profile_version_dataset_id),
                voice_profile_version_id=str(d.voice_profile_version_id),
                dataset_id=str(d.dataset_id),
                dataset_name=d.dataset_name,
                source_profile=d.source_profile,
                sample_size=d.sample_size,
                sample_scope_note=d.sample_scope_note,
                created_at=to_utc_iso(d.created_at) if d.created_at else None,
                updated_at=to_utc_iso(d.updated_at) if d.updated_at else None,
            )
            for d in datasets
        ],
    )
    return VoiceProfileGenerateResponse(
        collection=collection_entity,
        generated_version=version_detail,
        dataset_entries_written=written,
    )


@router.get("/versions/{voice_profile_version_id}", response_model=VoiceProfileVersionDetailResponse)
def get_version(
    voice_profile_version_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileVersionDetailResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    try:
        version_uuid = uuid.UUID(voice_profile_version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid voice_profile_version_id") from exc
    version = repo.get_version(version_uuid)
    if version is None:
        raise HTTPException(status_code=404, detail="Voice profile version not found")
    datasets = repo.list_version_datasets(version_uuid)
    return VoiceProfileVersionDetailResponse(
        version=_to_version_summary(version),
        raw_profile_json=version.raw_profile_json or {},
        style_summary=version.style_summary or {},
        tone_baseline=version.tone_baseline or {},
        do_rules=[str(x) for x in (version.do_rules or [])],
        dont_rules=[str(x) for x in (version.dont_rules or [])],
        datasets=[
            VoiceProfileVersionDatasetEntity(
                voice_profile_version_dataset_id=str(d.voice_profile_version_dataset_id),
                voice_profile_version_id=str(d.voice_profile_version_id),
                dataset_id=str(d.dataset_id),
                dataset_name=d.dataset_name,
                source_profile=d.source_profile,
                sample_size=d.sample_size,
                sample_scope_note=d.sample_scope_note,
                created_at=to_utc_iso(d.created_at) if d.created_at else None,
                updated_at=to_utc_iso(d.updated_at) if d.updated_at else None,
            )
            for d in datasets
        ],
    )


@router.post("/versions/{voice_profile_version_id}/activate", response_model=VoiceProfileVersionSummary)
def activate_version(
    voice_profile_version_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileVersionSummary:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    try:
        version_uuid = uuid.UUID(voice_profile_version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid voice_profile_version_id") from exc
    try:
        row = repo.activate_version(version_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_version_summary(row)


@router.post("/versions/{voice_profile_version_id}/status", response_model=VoiceProfileVersionSummary)
def update_version_status(
    voice_profile_version_id: str,
    payload: VersionStatusUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileVersionSummary:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    try:
        version_uuid = uuid.UUID(voice_profile_version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid voice_profile_version_id") from exc
    try:
        row = repo.update_version_status(version_uuid, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_version_summary(row)
