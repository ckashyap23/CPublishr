from __future__ import annotations

import json
import os
import uuid
import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from src.core.config import settings
from src.db.repositories.voice_profile_module_repository import VoiceProfileModuleRepository
from src.schemas.voice_profiles import DatasetGenerateInput
from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object

logger = logging.getLogger(__name__)


def _get_blob_service_client():
    """
    Lazy import so we don't cache a missing optional dependency at module import time.
    This makes local iteration nicer (installing the package doesn't require a full server restart).
    """
    try:
        from azure.storage.blob import BlobServiceClient  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "azure-storage-blob is not installed. "
            "Install it in your backend environment (e.g. `pip install azure-storage-blob`)."
        ) from exc
    return BlobServiceClient


def _sanitize_connection_string(raw: str) -> str:
    """
    Tolerate a common typo:
    DefaultEndpointsProtocol=DefaultEndpointsProtocol=https;...
    """
    s = (raw or "").strip()
    bad = "DefaultEndpointsProtocol=DefaultEndpointsProtocol="
    if s.startswith(bad):
        s = "DefaultEndpointsProtocol=" + s[len(bad) :]
    return s


ALLOWED_ENTRY_TYPES = {
    "text_post",
    "carousel",
    "image_post",
    "video",
    "reel",
    "short_video",
    "podcast_clip",
    "thread",
    "email",
    "blog_post",
    "other",
}

TEXT_EXTS = {".txt", ".md", ".json", ".csv", ".srt", ".vtt"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _infer_entry_type(blob_name: str) -> str:
    ext = Path(blob_name).suffix.lower()
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image_post"
    if ext in TEXT_EXTS:
        return "text_post"
    return "other"


def _normalize_platforms(platforms: list[str]) -> list[str]:
    return sorted({str(p).strip().lower() for p in platforms if str(p).strip()})


def _connection_account_name(conn_str: str) -> str | None:
    parts = [p.strip() for p in (conn_str or "").split(";") if p.strip()]
    kv: dict[str, str] = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv.get("AccountName")


def _blob_uri(account_name: str | None, container: str, blob_name: str) -> str:
    if account_name:
        return f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}"
    return f"{container}/{blob_name}"


def _normalize_blob_prefix(raw_prefix: str, container: str) -> str:
    """
    Accepts either:
    - relative prefix: user_id/dataset_name/
    - full blob URL: https://<acct>.blob.core.windows.net/<container>/user_id/dataset_name/
    and returns container-relative prefix.
    """
    s = (raw_prefix or "").strip()
    if not s:
        return ""
    parsed = urlparse(s)
    if parsed.scheme and parsed.netloc:
        path = (parsed.path or "").lstrip("/")
        container_prefix = f"{container}/"
        if path.startswith(container_prefix):
            s = path[len(container_prefix) :]
        else:
            s = path
    return s.lstrip("/")


def _coerce_to_object(value: Any, *, fallback_key: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        return {fallback_key: value.strip()}
    return {}


def _coerce_to_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


@dataclass
class IngestResult:
    dataset_id: uuid.UUID
    dataset_name: str
    source_profile: str | None
    sample_scope_note: str | None
    entry_count: int


class VoiceProfileModuleService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.repo = VoiceProfileModuleRepository(db, user_id=user_id)
        self.llm = AzureOpenAIClient()

    def create_collection(self, *, voice_profile_name: str, platforms: list[str]):
        normalized_platforms = _normalize_platforms(platforms)
        if not voice_profile_name.strip():
            raise ValueError("voice_profile_name is required")
        if not normalized_platforms:
            raise ValueError("at least one platform is required")
        return self.repo.create_collection(voice_profile_name=voice_profile_name, platforms=normalized_platforms)

    def ingest_dataset_from_blob(self, payload: DatasetGenerateInput) -> IngestResult:
        BlobServiceClient = _get_blob_service_client()
        conn_str = _sanitize_connection_string(settings.azure_storage_connection_string)
        container = settings.azure_profile_entries_container
        if not conn_str:
            raise ValueError("azure_storage_connection_string is required in settings")
        if not container:
            raise ValueError("azure_profile_entries_container is required in settings")

        dataset_id = uuid.UUID(payload.dataset_id) if payload.dataset_id else uuid.uuid4()
        prefix = _normalize_blob_prefix(payload.blob_prefix, container)

        try:
            svc = BlobServiceClient.from_connection_string(conn_str)
            container_client = svc.get_container_client(container)
        except Exception as exc:
            raise ValueError(f"Invalid Azure Storage connection configuration: {exc}") from exc
        account_name = _connection_account_name(conn_str)

        count = 0
        matched = 0
        seen_blob_names: set[str] = set()
        prefix_candidates = []
        if prefix:
            prefix_candidates.append(prefix)
            if prefix.endswith("/"):
                prefix_candidates.append(prefix.rstrip("/"))
            else:
                prefix_candidates.append(f"{prefix}/")
        else:
            prefix_candidates.append("")

        with TemporaryDirectory(prefix="vp_blob_") as tmpdir:
            local_root = Path(tmpdir)

            def persist_blob(blob_name: str) -> None:
                nonlocal count, matched
                if blob_name.endswith("/") or blob_name in seen_blob_names:
                    return
                seen_blob_names.add(blob_name)
                matched += 1

                entry_id = uuid.uuid4()
                entry_type = _infer_entry_type(blob_name)
                target = local_root / Path(blob_name).name
                target.parent.mkdir(parents=True, exist_ok=True)

                text_clean = None
                if Path(blob_name).suffix.lower() in TEXT_EXTS:
                    stream = container_client.download_blob(blob_name)
                    target.write_bytes(stream.readall())
                    try:
                        text_clean = target.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        text_clean = None

                self.repo.upsert_dataset_entry(
                    entry_id=entry_id,
                    dataset_id=dataset_id,
                    blob_uri=_blob_uri(account_name, container, blob_name),
                    source_url=None,
                    date_month_year=None,
                    text_clean=text_clean,
                    reactions=None,
                    comments=None,
                    total_visible=None,
                    metadata_asset=Path(blob_name).name,
                    entry_type=entry_type if entry_type in ALLOWED_ENTRY_TYPES else "other",
                    format_family=None,
                    hook_type=None,
                    cta_type=None,
                    cta_present=None,
                    theme_tags=[],
                )
                count += 1

            # 1) prefix listing mode (folder or exact blob-name prefix)
            list_error: Exception | None = None
            try:
                for candidate in prefix_candidates:
                    for blob in container_client.list_blobs(name_starts_with=candidate):
                        persist_blob(str(blob.name))
            except Exception as exc:  # azure exceptions vary across sdk versions
                list_error = exc

            # 2) direct single-blob fallback for full URL/file path inputs
            if matched == 0:
                direct_blob_name = prefix.rstrip("/")
                if direct_blob_name and Path(direct_blob_name).suffix:
                    try:
                        stream = container_client.download_blob(direct_blob_name)
                        stream.readall()  # verify blob exists/readable
                        persist_blob(direct_blob_name)
                    except Exception as exc:
                        if list_error is not None:
                            raise ValueError(
                                f"Failed to read dataset blob '{direct_blob_name}' in container '{container}'. "
                                f"list_blobs error: {list_error}; download_blob error: {exc}"
                            ) from exc
                        raise ValueError(
                            f"Failed to read dataset blob '{direct_blob_name}' in container '{container}': {exc}"
                        ) from exc

        if matched == 0:
            raise ValueError(
                f"No blobs found for prefix '{prefix}' in container '{container}'. "
                f"Tried candidates: {prefix_candidates}. "
                "Use container-relative prefix like 'user_id/dataset_name/' or a full blob URL."
            )

        return IngestResult(
            dataset_id=dataset_id,
            dataset_name=payload.dataset_name,
            source_profile=payload.source_profile,
            sample_scope_note=payload.sample_scope_note,
            entry_count=count,
        )

    def _generate_profile_json(self, entries_payload: list[dict[str, Any]], intended_use: str | None) -> dict[str, Any]:
        if not entries_payload:
            return {
                "intended_use": intended_use,
                "core_voice": None,
                "style_summary": {"sample_scope_note": "No entries found"},
                "tone_baseline": {},
                "do_rules": [],
                "dont_rules": [],
            }

        system_prompt = (
            "You are a strict JSON generator for creator voice profiling. "
            "Return only a JSON object with keys: intended_use, core_voice, style_summary, tone_baseline, do_rules, dont_rules."
        )
        user_prompt = (
            "Generate a creator voice profile from these dataset entries. "
            "Do not hallucinate. Keep fields compact and structured.\n\n"
            f"intended_use: {intended_use}\n"
            f"entries: {json.dumps(entries_payload, ensure_ascii=False)[:30000]}"
        )
        if not self.llm.enabled:
            return {
                "intended_use": intended_use,
                "core_voice": "Confident, practical, and concise",
                "style_summary": {"sample_scope_note": f"Generated from {len(entries_payload)} entries"},
                "tone_baseline": {"directness": 0.7, "warmth": 0.5},
                "do_rules": ["Use crisp hooks", "Use practical examples"],
                "dont_rules": ["Avoid vague claims"],
            }

        try:
            response = self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2, max_tokens=1500)
            parsed = parse_json_object(response)
            if not isinstance(parsed, dict) or not parsed:
                raise ValueError("LLM returned invalid profile JSON")
            return parsed
        except Exception as exc:
            logger.exception("Voice profile LLM generation failed; using fallback profile JSON")
            return {
                "intended_use": intended_use,
                "core_voice": "Clear, direct, and practical",
                "style_summary": {
                    "sample_scope_note": f"Fallback profile generated from {len(entries_payload)} entries",
                    "model_error": f"{exc.__class__.__name__}: {str(exc)}",
                },
                "tone_baseline": {"directness": 0.7, "warmth": 0.5},
                "do_rules": ["Open with a specific hook", "Use concrete examples"],
                "dont_rules": ["Avoid abstract filler", "Avoid vague claims"],
            }

    def generate_new_version(
        self,
        *,
        voice_profile_id: uuid.UUID,
        intended_use: str | None,
        datasets: list[DatasetGenerateInput],
    ):
        try:
            collection = self.repo.get_collection(voice_profile_id)
            if collection is None:
                raise ValueError("Voice profile collection not found")

            ingest_results: list[IngestResult] = []
            for ds in datasets:
                ingest_results.append(self.ingest_dataset_from_blob(ds))

            # NOTE:
            # Our SQLAlchemy Session is configured with autoflush=False (see src/db/session.py).
            # `ingest_dataset_from_blob()` queues DatasetEntry inserts via `db.add(...)`, but without a flush
            # a subsequent SELECT won't "see" those pending inserts. That leads to empty `entries` here and
            # placeholder/empty voice profile fields.
            #
            # Flushing ensures dataset_entries are written to the DB within the current transaction
            # before we query them back to build the LLM input payload.
            self.db.flush()

            entries: list[dict[str, Any]] = []
            for r in ingest_results:
                rows = self.repo.list_dataset_entries(r.dataset_id)
                for e in rows:
                    entries.append(
                        {
                            "entry_id": str(e.entry_id),
                            "dataset_id": str(e.dataset_id),
                            "entry_type": e.entry_type,
                            "text_clean": e.text_clean,
                            "blob_uri": e.blob_uri,
                            "metadata_asset": e.metadata_asset,
                        }
                    )

            profile_json = self._generate_profile_json(entries, intended_use)
            style_summary_obj = _coerce_to_object(profile_json.get("style_summary"), fallback_key="summary")
            tone_baseline_obj = _coerce_to_object(profile_json.get("tone_baseline"), fallback_key="baseline")
            do_rules_list = _coerce_to_string_list(profile_json.get("do_rules"))
            dont_rules_list = _coerce_to_string_list(profile_json.get("dont_rules"))

            normalized_raw_profile_json = dict(profile_json)
            normalized_raw_profile_json["style_summary"] = style_summary_obj
            normalized_raw_profile_json["tone_baseline"] = tone_baseline_obj
            normalized_raw_profile_json["do_rules"] = do_rules_list
            normalized_raw_profile_json["dont_rules"] = dont_rules_list

            version = self.repo.create_generated_version(
                voice_profile_id=voice_profile_id,
                intended_use=profile_json.get("intended_use") if isinstance(profile_json.get("intended_use"), str) else intended_use,
                core_voice=profile_json.get("core_voice") if isinstance(profile_json.get("core_voice"), str) else None,
                style_summary=style_summary_obj,
                tone_baseline=tone_baseline_obj,
                do_rules=do_rules_list,
                dont_rules=dont_rules_list,
                raw_profile_json=normalized_raw_profile_json,
                generation_status="generated",
            )

            written = 0
            for r in ingest_results:
                self.repo.upsert_version_dataset(
                    voice_profile_version_id=version.voice_profile_version_id,
                    dataset_id=r.dataset_id,
                    dataset_name=r.dataset_name,
                    source_profile=r.source_profile,
                    sample_size=r.entry_count,
                    sample_scope_note=r.sample_scope_note,
                )
                written += r.entry_count

            collection.updated_at = datetime.now(UTC)
            self.db.add(collection)
            self.db.commit()
            self.db.refresh(version)
            self.db.refresh(collection)
            return collection, version, written
        except Exception:
            self.db.rollback()
            raise
