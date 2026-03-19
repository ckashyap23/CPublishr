from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.db.models.voice_profile import VoiceProfile
from src.db.models.voice_profile_collection import VoiceProfileCollection
from src.db.models.voice_profile_dataset import VoiceProfileDataset
from src.db.models.voice_profile_version import VoiceProfileVersion
from src.db.repositories.voice_profile_module_repository import VoiceProfileModuleRepository
from src.schemas.voice_profiles import (
    VersionStatusUpdateRequest,
    VoiceProfileCollectionCreateRequest,
    VoiceProfileCollectionDetailResponse,
    VoiceProfileCollectionEntity,
    VoiceProfileCollectionListResponse,
    VoiceProfileCreateRequest,
    VoiceProfileCreateResponse,
    VoiceProfileDatasetCreateRequest,
    VoiceProfileDatasetCreateResponse,
    VoiceProfileDatasetEntity,
    VoiceProfileDetailResponse,
    VoiceProfileEntity,
    VoiceProfileGenerateRequest,
    VoiceProfileGenerateResponse,
    VoiceProfileListResponse,
    VoiceProfileStatusUpdateRequest,
    VoiceProfileVersionDatasetEntity,
    VoiceProfileVersionDetailResponse,
    VoiceProfileVersionSummary,
)
from src.services.voice_profiles.service import VoiceProfileModuleService
from src.utils.time import to_utc_iso

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_version_summary(v: VoiceProfileVersion) -> VoiceProfileVersionSummary:
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


def _to_dataset_entity(row: VoiceProfileDataset) -> VoiceProfileDatasetEntity:
    source_path = str(row.blob_prefix or "")
    source_type = "local_folder"
    lowered = source_path.lower()
    if lowered.startswith(("azure://", "az://", "http://", "https://")) or "/" in source_path:
        source_type = "azure_blob"
    return VoiceProfileDatasetEntity(
        dataset_id=str(row.dataset_id),
        collection_id=str(row.collection_id),
        user_id=row.user_id,
        dataset_name=row.dataset_name,
        source_profile=row.source_profile,
        source_type=source_type,
        blob_prefix=row.blob_prefix,
        sample_scope_note=row.sample_scope_note,
        entry_count=int(row.entry_count or 0),
        created_at=to_utc_iso(row.created_at) if row.created_at else None,
        updated_at=to_utc_iso(row.updated_at) if row.updated_at else None,
    )


def _to_collection_entity(collection: VoiceProfileCollection, datasets: list[VoiceProfileDataset], voice_profiles: list[VoiceProfile]) -> VoiceProfileCollectionEntity:
    return VoiceProfileCollectionEntity(
        collection_id=str(collection.collection_id),
        user_id=collection.user_id,
        collection_name=collection.collection_name,
        platforms=[str(x) for x in (collection.platforms or [])],
        dataset_count=len(datasets),
        voice_profile_count=len(voice_profiles),
        created_at=to_utc_iso(collection.created_at) if collection.created_at else None,
        updated_at=to_utc_iso(collection.updated_at) if collection.updated_at else None,
    )


def _to_voice_profile_entity(voice_profile: VoiceProfile, versions: list[VoiceProfileVersion]) -> VoiceProfileEntity:
    latest = versions[0] if versions else None
    active = next((x for x in versions if x.is_active), None)
    return VoiceProfileEntity(
        voice_profile_id=str(voice_profile.voice_profile_id),
        collection_id=str(voice_profile.collection_id),
        user_id=voice_profile.user_id,
        voice_profile_name=voice_profile.voice_profile_name,
        is_enabled=bool(getattr(voice_profile, "is_enabled", True)),
        latest_version=_to_version_summary(latest) if latest else None,
        active_version=_to_version_summary(active) if active else None,
        created_at=to_utc_iso(voice_profile.created_at) if voice_profile.created_at else None,
        updated_at=to_utc_iso(voice_profile.updated_at) if voice_profile.updated_at else None,
    )


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


@router.post("/collections", response_model=VoiceProfileCollectionDetailResponse)
def create_collection(
    payload: VoiceProfileCollectionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileCollectionDetailResponse:
    svc = VoiceProfileModuleService(db, user_id=user_id)
    try:
        collection = svc.create_collection(
            collection_name=payload.collection_name,
            platforms=payload.platforms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    entity = _to_collection_entity(collection, [], [])
    return VoiceProfileCollectionDetailResponse(collection=entity, datasets=[], voice_profiles=[])


@router.get("/collections", response_model=VoiceProfileCollectionListResponse)
def list_collections(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileCollectionListResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    rows = repo.list_collections()
    entities = []
    for row in rows:
        datasets = repo.list_datasets(row.collection_id)
        voice_profiles = repo.list_voice_profiles(row.collection_id)
        entities.append(_to_collection_entity(row, datasets, voice_profiles))
    return VoiceProfileCollectionListResponse(collections=entities)


@router.get("/collections/{collection_id}", response_model=VoiceProfileCollectionDetailResponse)
def get_collection(
    collection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileCollectionDetailResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    collection_uuid = _parse_uuid(collection_id, "collection_id")
    row = repo.get_collection(collection_uuid)
    if row is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    datasets = repo.list_datasets(collection_uuid)
    voice_profiles = repo.list_voice_profiles(collection_uuid)
    voice_profile_entities = []
    for voice_profile in voice_profiles:
        versions = repo.list_versions(voice_profile.voice_profile_id)
        voice_profile_entities.append(_to_voice_profile_entity(voice_profile, versions))
    return VoiceProfileCollectionDetailResponse(
        collection=_to_collection_entity(row, datasets, voice_profiles),
        datasets=[_to_dataset_entity(d) for d in datasets],
        voice_profiles=voice_profile_entities,
    )


@router.post("/collections/{collection_id}/datasets", response_model=VoiceProfileDatasetCreateResponse)
def create_dataset(
    collection_id: str,
    payload: VoiceProfileDatasetCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileDatasetCreateResponse:
    collection_uuid = _parse_uuid(collection_id, "collection_id")
    svc = VoiceProfileModuleService(db, user_id=user_id)
    try:
        result = svc.ingest_dataset_from_blob(collection_id=collection_uuid, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    collection = repo.get_collection(collection_uuid)
    datasets = repo.list_datasets(collection_uuid)
    voice_profiles = repo.list_voice_profiles(collection_uuid)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return VoiceProfileDatasetCreateResponse(
        collection=_to_collection_entity(collection, datasets, voice_profiles),
        dataset=_to_dataset_entity(result.dataset),
        dataset_entries_written=result.entry_count,
    )


@router.post("/collections/{collection_id}/profiles", response_model=VoiceProfileCreateResponse)
def create_voice_profile(
    collection_id: str,
    payload: VoiceProfileCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileCreateResponse:
    collection_uuid = _parse_uuid(collection_id, "collection_id")
    svc = VoiceProfileModuleService(db, user_id=user_id)
    try:
        collection, voice_profile = svc.create_voice_profile(
            collection_id=collection_uuid,
            voice_profile_name=payload.voice_profile_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    datasets = repo.list_datasets(collection_uuid)
    voice_profiles = repo.list_voice_profiles(collection_uuid)
    return VoiceProfileCreateResponse(
        collection=_to_collection_entity(collection, datasets, voice_profiles),
        voice_profile=_to_voice_profile_entity(voice_profile, []),
    )


@router.get("/profiles/{voice_profile_id}", response_model=VoiceProfileDetailResponse)
def get_voice_profile(
    voice_profile_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileDetailResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    voice_profile_uuid = _parse_uuid(voice_profile_id, "voice_profile_id")
    row = repo.get_voice_profile(voice_profile_uuid)
    if row is None:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    versions = repo.list_versions(voice_profile_uuid)
    return VoiceProfileDetailResponse(
        voice_profile=_to_voice_profile_entity(row, versions),
        versions=[_to_version_summary(v) for v in versions],
    )


@router.get("/profiles", response_model=VoiceProfileListResponse)
def list_voice_profiles(
    collection_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileListResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    collection_uuid = _parse_uuid(collection_id, "collection_id") if collection_id else None
    profiles = repo.list_voice_profiles(collection_uuid)
    entities = []
    for row in profiles:
        versions = repo.list_versions(row.voice_profile_id)
        entities.append(_to_voice_profile_entity(row, versions))
    return VoiceProfileListResponse(voice_profiles=entities)


@router.post("/profiles/{voice_profile_id}/status", response_model=VoiceProfileEntity)
def update_voice_profile_status(
    voice_profile_id: str,
    payload: VoiceProfileStatusUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileEntity:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    voice_profile_uuid = _parse_uuid(voice_profile_id, "voice_profile_id")
    try:
        row = repo.set_voice_profile_enabled(voice_profile_uuid, payload.is_enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    versions = repo.list_versions(voice_profile_uuid)
    return _to_voice_profile_entity(row, versions)


@router.delete("/profiles/{voice_profile_id}")
def delete_voice_profile(
    voice_profile_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    voice_profile_uuid = _parse_uuid(voice_profile_id, "voice_profile_id")
    try:
        repo.delete_voice_profile(voice_profile_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True, "voice_profile_id": voice_profile_id}


@router.post("/profiles/{voice_profile_id}/versions/generate", response_model=VoiceProfileGenerateResponse)
def generate_version(
    voice_profile_id: str,
    payload: VoiceProfileGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileGenerateResponse:
    voice_profile_uuid = _parse_uuid(voice_profile_id, "voice_profile_id")
    svc = VoiceProfileModuleService(db, user_id=user_id)
    try:
        voice_profile, version = svc.generate_new_version(
            voice_profile_id=voice_profile_uuid,
            intended_use=payload.intended_use,
            dataset_ids=payload.dataset_ids,
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
    versions = repo.list_versions(voice_profile_uuid)
    datasets = repo.list_version_datasets(version.voice_profile_version_id)
    return VoiceProfileGenerateResponse(
        voice_profile=_to_voice_profile_entity(voice_profile, versions),
        generated_version=VoiceProfileVersionDetailResponse(
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
        ),
    )


@router.get("/versions/{voice_profile_version_id}", response_model=VoiceProfileVersionDetailResponse)
def get_version(
    voice_profile_version_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> VoiceProfileVersionDetailResponse:
    repo = VoiceProfileModuleRepository(db, user_id=user_id)
    version_uuid = _parse_uuid(voice_profile_version_id, "voice_profile_version_id")
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
    version_uuid = _parse_uuid(voice_profile_version_id, "voice_profile_version_id")
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
    version_uuid = _parse_uuid(voice_profile_version_id, "voice_profile_version_id")
    try:
        row = repo.update_version_status(version_uuid, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_version_summary(row)
