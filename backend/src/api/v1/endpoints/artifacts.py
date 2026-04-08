import logging
from typing import Any
from urllib.parse import urlparse, parse_qs

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.contracts.prd import ArtifactEntity, ArtifactFormat, ArtifactKind, ArtifactListResponse
from src.core.config import settings
from src.db.repositories.artifact_repository import ArtifactRepository
from src.schemas.artifacts import (
    ArtifactEditRequest,
    ArtifactEditResponse,
    ArtifactGenerationRequest,
    ArtifactGenerationResponse,
    ArtifactSuggestRequest,
    ArtifactSuggestResponse,
    ArtifactTitleUpdateRequest,
)
from src.db.models.artifact import Artifact
from src.services.orchestration.artifact_schema import formats_by_kind_map
from src.services.orchestration.artifacts.contracts import GenerationOptions
from src.services.orchestration.artifacts.orchestrator import ArtifactPipelineOrchestrator
from src.services.storage.artifact_blob_storage import generate_read_url

router = APIRouter()
logger = logging.getLogger(__name__)


def _refresh_sas_urls_in_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Refresh expired SAS URLs in payload_json assets by regenerating them from blob_path."""
    if not isinstance(payload, dict):
        return payload
    
    payload = dict(payload)  # Make a copy
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        return payload
    
    container = settings.azure_artifacts_container or "artifacts"
    refreshed_assets = []
    
    for asset in assets:
        if not isinstance(asset, dict):
            refreshed_assets.append(asset)
            continue
        
        asset = dict(asset)  # Make a copy
        blob_path = asset.get("blob_path")
        uri = asset.get("uri", "")
        
        # If we have a blob_path, try to regenerate the SAS URL
        if blob_path and isinstance(blob_path, str) and blob_path.strip():
            new_uri = generate_read_url(container, blob_path.strip())
            if new_uri:
                asset["uri"] = new_uri
                logger.debug("Refreshed SAS URL for blob_path=%s", blob_path)
        # If no blob_path but we have a URI that looks like Azure Blob Storage, try to extract path
        elif uri and "blob.core.windows.net" in uri:
            try:
                parsed = urlparse(uri)
                # Extract blob path from URL: https://account.blob.core.windows.net/container/path/to/file
                # Remove query string (SAS token) first
                path_without_query = parsed.path
                path_parts = path_without_query.strip("/").split("/", 1)  # ['container', 'path/to/file']
                if len(path_parts) >= 2:
                    container_name = path_parts[0]
                    blob_path = path_parts[1]
                    new_uri = generate_read_url(container_name, blob_path)
                    if new_uri:
                        asset["uri"] = new_uri
                        asset["blob_path"] = blob_path  # Store for future refreshes
                        logger.debug("Refreshed SAS URL by extracting blob_path from URI: %s", blob_path)
            except Exception as e:
                logger.debug("Could not extract blob_path from URI %s: %s", uri[:100], e)
        
        refreshed_assets.append(asset)
    
    payload["assets"] = refreshed_assets
    return payload


def _to_entity(a: Artifact) -> ArtifactEntity:
    payload = a.payload_json or {}
    # Refresh SAS URLs in assets before returning
    payload = _refresh_sas_urls_in_payload(payload)
    
    return ArtifactEntity(
        artifact_id=a.artifact_id,
        project_id=a.project_id,
        format=a.format,
        kind=a.kind,
        title=a.title,
        payload_json=payload,
        tags_json=a.tags_json or [],
        status=a.status,
        revision=a.revision,
        parent_artifact_id=a.parent_artifact_id,
        created_at=(a.created_at.isoformat() if a.created_at else None),
        updated_at=(a.updated_at.isoformat() if a.updated_at else None),
    )


@router.get("/catalog/formats")
def list_artifact_formats_catalog() -> dict[str, dict[str, list[str]]]:
    try:
        return {"formats_by_kind": formats_by_kind_map()}
    except Exception as exc:
        logger.exception("Failed to load artifact formats catalog")
        raise HTTPException(status_code=500, detail="Failed to load artifact formats catalog") from exc


@router.patch("/item/{artifact_id}/title", response_model=ArtifactEntity)
def update_artifact_title(
    artifact_id: str,
    payload: ArtifactTitleUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactEntity:
    repo = ArtifactRepository(db, user_id=user_id)
    title = (str(payload.title).strip() if payload.title is not None else None)
    row = repo.update_title(artifact_id, title=title or None)
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _to_entity(row)


@router.post("/generate", response_model=ArtifactGenerationResponse)
def generate_artifacts(
    payload: ArtifactGenerationRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactGenerationResponse:
    orchestrator = ArtifactPipelineOrchestrator(db, user_id=user_id)
    requested_formats = payload.requested_formats or []
    try:
        out = orchestrator.generate(
            project_id=payload.project_id,
            requested_formats=[str(x) for x in requested_formats],
            options=GenerationOptions(revision_mode=payload.revision_mode),
            style_settings_by_kind=payload.style_settings_by_kind or {},
            style_settings_by_format=payload.style_settings_by_format or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Artifact generation failed for project_id=%s", payload.project_id)
        detail = str(exc).strip() or "Artifact generation failed"
        raise HTTPException(status_code=500, detail=detail[:2000]) from exc
    return ArtifactGenerationResponse.model_validate(out)


@router.post("/edit", response_model=ArtifactEditResponse)
def edit_artifact(
    payload: ArtifactEditRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactEditResponse:
    orchestrator = ArtifactPipelineOrchestrator(db, user_id=user_id)
    try:
        out = orchestrator.edit_artifact(
            artifact_id=payload.artifact_id,
            mode=payload.mode,
            inline_content=payload.inline_content,
            edit_instruction=payload.edit_instruction,
            style_settings_by_kind=payload.style_settings_by_kind or {},
            style_settings_by_format=payload.style_settings_by_format or {},
            source_blob_paths=payload.source_blob_paths or [],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Artifact edit failed for artifact_id=%s mode=%s", payload.artifact_id, payload.mode)
        detail = str(exc).strip() or "Artifact edit failed"
        raise HTTPException(status_code=500, detail=detail[:2000]) from exc
    return ArtifactEditResponse.model_validate(out)


@router.post("/suggest", response_model=ArtifactSuggestResponse)
def suggest_artifact_styles(
    payload: ArtifactSuggestRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactSuggestResponse:
    from src.services.orchestration.artifacts.artifact_suggestion import ArtifactSuggestionService

    svc = ArtifactSuggestionService(db, user_id=user_id)
    try:
        suggestions = svc.suggest(project_id=payload.project_id, formats=payload.formats)
    except Exception as exc:
        logger.exception("Artifact style suggestion failed for project_id=%s", payload.project_id)
        detail = str(exc).strip() or "Artifact style suggestion failed"
        raise HTTPException(status_code=500, detail=detail[:2000]) from exc
    return ArtifactSuggestResponse(suggestions=suggestions)


@router.get("/{project_id}", response_model=ArtifactListResponse)
def list_artifacts(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactListResponse:
    rows = ArtifactRepository(db, user_id=user_id).list_artifacts(project_id)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[_to_entity(a) for a in rows],
    )


@router.get("/{project_id}/{format}", response_model=ArtifactListResponse)
def list_artifacts_by_format(
    project_id: str,
    format: ArtifactFormat,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactListResponse:
    rows = ArtifactRepository(db, user_id=user_id).list_artifacts_by_format(project_id, format)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[_to_entity(a) for a in rows],
    )


@router.get("/{project_id}/kind/{kind}", response_model=ArtifactListResponse)
def list_artifacts_by_kind(
    project_id: str,
    kind: ArtifactKind,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ArtifactListResponse:
    rows = ArtifactRepository(db, user_id=user_id).list_artifacts_by_kind(project_id, kind)
    return ArtifactListResponse(
        project_id=project_id,
        artifacts=[_to_entity(a) for a in rows],
    )
