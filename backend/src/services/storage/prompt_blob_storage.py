from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)


def _get_blob_sdk() -> tuple[Any, Any]:
    try:
        from azure.storage.blob import BlobServiceClient, ContentSettings  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "azure-storage-blob is not installed. Install it in your backend environment "
            "(e.g. `pip install azure-storage-blob`)."
        ) from exc
    return BlobServiceClient, ContentSettings


def _sanitize_connection_string(raw: str) -> str:
    s = (raw or "").strip()
    bad = "DefaultEndpointsProtocol=DefaultEndpointsProtocol="
    if s.startswith(bad):
        s = "DefaultEndpointsProtocol=" + s[len(bad) :]
    return s


def _slug_segment(value: str, *, default: str, max_len: int = 120) -> str:
    s = re.sub(r"[^\w\-./ ]", "_", (value or "").strip())[:max_len]
    s = s.replace(" ", "_").strip("_./")
    return s or default


def _blob_exists(container_client: Any, blob_path: str) -> bool:
    try:
        blob_client = container_client.get_blob_client(blob_path)
        return bool(blob_client.exists())
    except Exception:
        return False


def _prompt_logging_enabled() -> bool:
    return bool(settings.azure_prompt_logging_enabled)


def format_chat_prompt_text(*, system_prompt: str, user_prompt: str) -> str:
    return (
        "SYSTEM PROMPT:\n"
        f"{system_prompt or ''}\n\n"
        "USER PROMPT:\n"
        f"{user_prompt or ''}\n"
    ).strip()


def save_prompt_text(
    *,
    user_id: str,
    project_id: str,
    section: str,
    name: str,
    text: str,
    subfolder: str | None = None,
    suffix: str | None = None,
    content_type: str = "text/plain; charset=utf-8",
) -> dict[str, str] | None:
    if not _prompt_logging_enabled():
        return None
    conn_str = _sanitize_connection_string(settings.azure_storage_connection_string)
    container = (settings.azure_prompts_container or "qc-prompts").strip() or "qc-prompts"
    if not conn_str or not container:
        logger.warning("Prompt logging skipped: missing connection string or prompts container config")
        return None

    prefix = _slug_segment(settings.azure_prompts_blob_prefix or "", default="", max_len=120)
    user_seg = _slug_segment(user_id, default="user", max_len=80)
    project_seg = _slug_segment(project_id, default="project", max_len=120)
    section_seg = _slug_segment(section, default="misc", max_len=80)
    subfolder_seg = _slug_segment(subfolder or "", default="", max_len=80) if subfolder else ""
    base_name = _slug_segment(name, default="prompt", max_len=140)
    suffix_seg = _slug_segment(suffix or "", default="", max_len=80) if suffix else ""
    file_stem = f"{base_name}_{suffix_seg}" if suffix_seg else base_name
    file_name = f"{file_stem}.txt"

    path_parts = [p for p in [prefix, user_seg, project_seg, section_seg, subfolder_seg, file_name] if p]
    blob_path = "/".join(path_parts)

    try:
        BlobServiceClient, ContentSettings = _get_blob_sdk()
        svc = BlobServiceClient.from_connection_string(conn_str)
        container_client = svc.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass

        # Keep filename stable when possible, but avoid overwrite by appending UTC timestamp.
        if _blob_exists(container_client, blob_path):
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            file_name = f"{file_stem}_{ts}.txt"
            path_parts = [p for p in [prefix, user_seg, project_seg, section_seg, subfolder_seg, file_name] if p]
            blob_path = "/".join(path_parts)

            # Absolute collision fallback.
            if _blob_exists(container_client, blob_path):
                file_name = f"{file_stem}_{ts}_{int(datetime.now(UTC).timestamp())}.txt"
                path_parts = [p for p in [prefix, user_seg, project_seg, section_seg, subfolder_seg, file_name] if p]
                blob_path = "/".join(path_parts)

        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(
            (text or "").encode("utf-8"),
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )
        return {"uri": blob_client.url, "blob_path": blob_path}
    except Exception as exc:
        logger.warning("Prompt logging failed for blob_path=%s: %s", blob_path, exc)
        return None

