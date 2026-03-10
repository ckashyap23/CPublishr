from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.core.config import settings

logger = logging.getLogger(__name__)


def _get_blob_sdk() -> tuple[Any, Any, Any, Any]:
    try:
        from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "azure-storage-blob is not installed. Install it in your backend environment "
            "(e.g. `pip install azure-storage-blob`)."
        ) from exc
    return BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions


def _sanitize_connection_string(raw: str) -> str:
    s = (raw or "").strip()
    bad = "DefaultEndpointsProtocol=DefaultEndpointsProtocol="
    if s.startswith(bad):
        s = "DefaultEndpointsProtocol=" + s[len(bad) :]
    return s


def _conn_parts(conn_str: str) -> dict[str, str]:
    parts = [p.strip() for p in (conn_str or "").split(";") if p.strip()]
    out: dict[str, str] = {}
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _slug_segment(value: str, *, default: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\-./]", "_", (value or "").strip())[:max_len]
    s = s.strip("_./")
    return s or default


def _filename_with_ext(filename: str, *, default_name: str) -> str:
    raw = Path(filename or "").name
    if not raw:
        return default_name
    return _slug_segment(raw, default=default_name, max_len=160)


def _artifacts_enabled() -> bool:
    return bool(settings.azure_artifacts_enabled)


def make_blob_path(user_id: str, project_id: str, format: str, artifact_id: str, filename: str) -> str:
    prefix = _slug_segment(settings.azure_artifacts_blob_prefix, default="artifacts", max_len=120)
    user_seg = _slug_segment(user_id, default="user", max_len=64)
    project_seg = _slug_segment(project_id, default="project", max_len=64)
    fmt_seg = _slug_segment(format, default="artifact_format", max_len=64)
    artifact_seg = _slug_segment(artifact_id, default="artifact_obj", max_len=120)
    file_seg = _filename_with_ext(filename, default_name="artifact.bin")
    return f"{prefix}/{user_seg}/{project_seg}/{fmt_seg}/{artifact_seg}/{file_seg}"


def generate_read_url(container: str, blob_path: str) -> str | None:
    conn_str = _sanitize_connection_string(settings.azure_storage_connection_string)
    if not conn_str or not container or not blob_path:
        return None
    parts = _conn_parts(conn_str)
    account_name = parts.get("AccountName")
    account_key = parts.get("AccountKey")
    if not account_name:
        return None
    base_url = f"https://{account_name}.blob.core.windows.net/{container}/{blob_path}"
    if settings.azure_artifacts_public_read:
        return base_url
    if not account_key:
        logger.warning("Azure artifact SAS URL requested but AccountKey missing in connection string")
        return None
    _, _, generate_blob_sas, BlobSasPermissions = _get_blob_sdk()
    expiry = datetime.now(UTC) + timedelta(minutes=max(1, int(settings.azure_artifacts_sas_ttl_minutes or 60)))
    token = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_path,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
    )
    return f"{base_url}?{token}" if token else base_url


def upload_bytes(
    *,
    data: bytes,
    user_id: str,
    project_id: str,
    format: str,
    artifact_id: str,
    filename: str,
    content_type: str,
) -> dict[str, str] | None:
    if not _artifacts_enabled():
        return None
    conn_str = _sanitize_connection_string(settings.azure_storage_connection_string)
    container = (settings.azure_artifacts_container or "").strip()
    if not conn_str or not container:
        logger.warning("Azure artifact upload skipped: missing connection string or artifacts container config")
        return None
    blob_path = make_blob_path(user_id, project_id, format, artifact_id, filename)
    try:
        BlobServiceClient, ContentSettings, _, _ = _get_blob_sdk()
        svc = BlobServiceClient.from_connection_string(conn_str)
        container_client = svc.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        uri = generate_read_url(container, blob_path)
        if not uri:
            uri = blob_client.url
        return {"uri": uri, "blob_path": blob_path}
    except Exception as exc:
        logger.warning("Azure artifact upload failed for blob_path=%s: %s", blob_path, exc)
        return None


def upload_text(
    *,
    text: str,
    user_id: str,
    project_id: str,
    format: str,
    artifact_id: str,
    filename: str,
    content_type: str = "text/plain; charset=utf-8",
) -> dict[str, str] | None:
    return upload_bytes(
        data=(text or "").encode("utf-8"),
        user_id=user_id,
        project_id=project_id,
        format=format,
        artifact_id=artifact_id,
        filename=filename,
        content_type=content_type,
    )


def overwrite_blob_text(
    *,
    blob_path: str,
    text: str,
    content_type: str = "text/plain; charset=utf-8",
) -> dict[str, str] | None:
    if not _artifacts_enabled():
        return None
    conn_str = _sanitize_connection_string(settings.azure_storage_connection_string)
    container = (settings.azure_artifacts_container or "").strip()
    if not conn_str or not container or not (blob_path or "").strip():
        logger.warning("Azure artifact overwrite skipped: missing config or blob_path")
        return None
    try:
        BlobServiceClient, ContentSettings, _, _ = _get_blob_sdk()
        svc = BlobServiceClient.from_connection_string(conn_str)
        container_client = svc.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_path.strip())
        blob_client.upload_blob(
            (text or "").encode("utf-8"),
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        uri = generate_read_url(container, blob_path.strip())
        if not uri:
            uri = blob_client.url
        return {"uri": uri, "blob_path": blob_path.strip()}
    except Exception as exc:
        logger.warning("Azure artifact overwrite failed for blob_path=%s: %s", blob_path, exc)
        return None


def blob_path_from_uri(uri: str) -> str | None:
    raw = str(uri or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
        path = str(parsed.path or "").strip("/")
        if not path:
            return None
        parts = path.split("/", 1)
        if len(parts) < 2:
            return None
        return parts[1].strip() or None
    except Exception:
        return None


def download_bytes(
    *,
    blob_path: str,
    container: str | None = None,
) -> bytes | None:
    if not _artifacts_enabled():
        return None
    clean_blob_path = str(blob_path or "").strip()
    if not clean_blob_path:
        return None
    conn_str = _sanitize_connection_string(settings.azure_storage_connection_string)
    resolved_container = str(container or settings.azure_artifacts_container or "").strip()
    if not conn_str or not resolved_container:
        logger.warning("Azure artifact download skipped: missing connection string or artifacts container config")
        return None
    try:
        BlobServiceClient, _, _, _ = _get_blob_sdk()
        svc = BlobServiceClient.from_connection_string(conn_str)
        container_client = svc.get_container_client(resolved_container)
        blob_client = container_client.get_blob_client(clean_blob_path)
        return blob_client.download_blob().readall()
    except Exception as exc:
        logger.warning("Azure artifact download failed for blob_path=%s: %s", clean_blob_path, exc)
        return None
