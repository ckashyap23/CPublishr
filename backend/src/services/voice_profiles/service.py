from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse
import re

from sqlalchemy.orm import Session

from src.core.config import settings
from src.db.models.voice_profile_dataset import VoiceProfileDataset
from src.db.repositories.voice_profile_module_repository import VoiceProfileModuleRepository
from src.schemas.voice_profiles import VoiceProfileDatasetCreateRequest
from src.services.llm.client import chat, is_enabled, parse_json_object

logger = logging.getLogger(__name__)


def _get_blob_service_client():
    try:
        from azure.storage.blob import BlobServiceClient  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "azure-storage-blob is not installed. "
            "Install it in your backend environment (e.g. `pip install azure-storage-blob`)."
        ) from exc
    return BlobServiceClient


def _sanitize_connection_string(raw: str) -> str:
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


def _is_local_path(value: str) -> bool:
    s = str(value or "").strip()
    if not s:
        return False
    lowered = s.lower()
    if lowered.startswith("file://"):
        return True
    if re.match(r"^[a-zA-Z]:[\\/]", s):
        return True
    if s.startswith(("\\\\", "/")):
        return True
    return False


def _normalize_local_path(raw_path: str) -> Path:
    s = str(raw_path or "").strip()
    if s.lower().startswith("file://"):
        parsed = urlparse(s)
        s = parsed.path or ""
        if re.match(r"^/[A-Za-z]:", s):
            s = s[1:]
    return Path(s)


def _normalize_local_file_paths(raw_value: str) -> list[Path]:
    s = str(raw_value or "").strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return [_normalize_local_path(str(item)) for item in parsed if str(item).strip()]
    return [_normalize_local_path(s)]


def _parse_azure_source(raw_path: str, default_container: str) -> tuple[str, str]:
    s = str(raw_path or "").strip()
    parsed = urlparse(s)
    if parsed.scheme.lower() in {"azure", "az"}:
        container = (parsed.netloc or "").strip()
        if not container:
            raise ValueError("Azure dataset source must include a container, e.g. azure://profile-entries/user_id/dataset/")
        prefix = (parsed.path or "").strip().strip("/")
        return container, prefix
    return default_container, _normalize_blob_prefix(s, default_container)


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
    dataset: VoiceProfileDataset
    entry_count: int


class VoiceProfileModuleService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.repo = VoiceProfileModuleRepository(db, user_id=user_id)
        

    def create_collection(self, *, collection_name: str, platforms: list[str]):
        normalized_platforms = _normalize_platforms(platforms)
        if not collection_name.strip():
            raise ValueError("collection_name is required")
        if not normalized_platforms:
            raise ValueError("at least one platform is required")
        return self.repo.create_collection(collection_name=collection_name, platforms=normalized_platforms)

    def create_voice_profile(self, *, collection_id: uuid.UUID, voice_profile_name: str):
        collection = self.repo.get_collection(collection_id)
        if collection is None:
            raise ValueError("Collection not found")
        normalized_name = voice_profile_name.strip()
        if not normalized_name:
            raise ValueError("voice_profile_name is required")
        existing_profiles = self.repo.list_voice_profiles(collection_id)
        if any(str(profile.voice_profile_name or "").strip().lower() == normalized_name.lower() for profile in existing_profiles):
            raise ValueError("A voice profile with this name already exists in the selected collection")
        return collection, self.repo.create_voice_profile(
            collection_id=collection_id,
            voice_profile_name=normalized_name,
        )

    def create_manual_version(
        self,
        *,
        voice_profile_id: uuid.UUID,
        intended_use: str | None,
        core_voice: str | None,
        summary: str | None,
        do_rules: list[str],
        dont_rules: list[str],
    ):
        try:
            voice_profile = self.repo.get_voice_profile(voice_profile_id)
            if voice_profile is None:
                raise ValueError("Voice profile not found")

            normalized_intended_use = str(intended_use or "").strip() or None
            normalized_core_voice = str(core_voice or "").strip() or None
            normalized_summary = str(summary or "").strip() or None
            normalized_do_rules = _coerce_to_string_list(do_rules)
            normalized_dont_rules = _coerce_to_string_list(dont_rules)

            version = self.repo.create_manual_version(
                voice_profile_id=voice_profile_id,
                intended_use=normalized_intended_use,
                core_voice=normalized_core_voice,
                summary=normalized_summary,
                do_rules=normalized_do_rules,
                dont_rules=normalized_dont_rules,
            )
            voice_profile.updated_at = version.updated_at
            self.db.add(voice_profile)
            self.db.commit()
            version = self.repo.activate_version(version.voice_profile_version_id)
            self.db.refresh(voice_profile)
            return voice_profile, version
        except Exception:
            self.db.rollback()
            raise

    def ingest_dataset_from_blob(
        self,
        *,
        collection_id: uuid.UUID,
        payload: VoiceProfileDatasetCreateRequest,
    ) -> IngestResult:
        collection = self.repo.get_collection(collection_id)
        if collection is None:
            raise ValueError("Collection not found")

        source_type = str(payload.source_type or "").strip().lower()
        dataset = self.repo.create_dataset(
            collection_id=collection_id,
            dataset_name=payload.dataset_name,
            source_profile=(payload.source_profile or "").strip() or None,
            blob_prefix=payload.blob_prefix,
            sample_scope_note=(payload.sample_scope_note or "").strip() or None,
        )
        try:
            if source_type.startswith("local") or _is_local_path(payload.blob_prefix) or str(payload.blob_prefix).strip().startswith("["):
                count = self._ingest_dataset_from_local_files(dataset=dataset, source_path=payload.blob_prefix)
            else:
                count = self._ingest_dataset_from_azure_blob(dataset=dataset, source_path=payload.blob_prefix)
        except Exception:
            self.db.rollback()
            raise

        self.repo.update_dataset_entry_count(dataset.dataset_id, count)
        collection.updated_at = dataset.updated_at
        self.db.add(collection)
        self.db.commit()
        self.db.refresh(dataset)
        self.db.refresh(collection)
        return IngestResult(dataset=dataset, entry_count=count)

    def _ingest_dataset_from_local_files(self, *, dataset: VoiceProfileDataset, source_path: str) -> int:
        files = _normalize_local_file_paths(source_path)
        if not files:
            raise ValueError("No local files were provided")

        count = 0
        for file_path in files:
            if not file_path.exists():
                raise ValueError(f"Local dataset file not found: {str(file_path)}")
            if not file_path.is_file():
                raise ValueError(f"Local dataset source must be a file: {str(file_path)}")
            text_clean = None
            if file_path.suffix.lower() in TEXT_EXTS:
                try:
                    text_clean = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    text_clean = None

            self.repo.upsert_dataset_entry(
                entry_id=uuid.uuid4(),
                dataset_id=dataset.dataset_id,
                blob_uri=file_path.resolve().as_uri(),
                source_url=None,
                date_month_year=None,
                text_clean=text_clean,
                reactions=None,
                comments=None,
                total_visible=None,
                metadata_asset=file_path.name,
                entry_type=_infer_entry_type(file_path.name),
                format_family=None,
                hook_type=None,
                cta_type=None,
                cta_present=None,
                theme_tags=[],
            )
            count += 1

        if count == 0:
            raise ValueError("No files were ingested from local dataset selection")
        return count

    def _ingest_dataset_from_azure_blob(self, *, dataset: VoiceProfileDataset, source_path: str) -> int:
        BlobServiceClient = _get_blob_service_client()
        conn_str = _sanitize_connection_string(settings.azure_storage_connection_string)
        default_container = settings.azure_profile_entries_container
        if not conn_str:
            raise ValueError("azure_storage_connection_string is required in settings")
        if not default_container:
            raise ValueError("azure_profile_entries_container is required in settings")

        container, prefix = _parse_azure_source(source_path, default_container)
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
                    entry_id=uuid.uuid4(),
                    dataset_id=dataset.dataset_id,
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

            list_error: Exception | None = None
            try:
                for candidate in prefix_candidates:
                    for blob in container_client.list_blobs(name_starts_with=candidate):
                        persist_blob(str(blob.name))
            except Exception as exc:
                list_error = exc

            if matched == 0:
                direct_blob_name = prefix.rstrip("/")
                if direct_blob_name and Path(direct_blob_name).suffix:
                    try:
                        stream = container_client.download_blob(direct_blob_name)
                        stream.readall()
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
                f"No blobs found for source '{source_path}' in container '{container}'. "
                f"Tried candidates: {prefix_candidates}."
            )
        return count

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
            "Only use the selected datasets represented here. "
            "Do not hallucinate. Keep fields compact and structured.\n\n"
            f"intended_use: {intended_use}\n"
            f"entries: {json.dumps(entries_payload, ensure_ascii=False)[:30000]}"
        )
        if not is_enabled():
            return {
                "intended_use": intended_use,
                "core_voice": "Confident, practical, and concise",
                "style_summary": {"sample_scope_note": f"Generated from {len(entries_payload)} selected entries"},
                "tone_baseline": {"directness": 0.7, "warmth": 0.5},
                "do_rules": ["Use crisp hooks", "Use practical examples"],
                "dont_rules": ["Avoid vague claims"],
            }

        try:
            response = chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2, max_tokens=1500)
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
                    "sample_scope_note": f"Fallback profile generated from {len(entries_payload)} selected entries",
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
        dataset_ids: list[str],
    ):
        try:
            voice_profile = self.repo.get_voice_profile(voice_profile_id)
            if voice_profile is None:
                raise ValueError("Voice profile not found")

            selected_datasets: list[VoiceProfileDataset] = []
            seen_dataset_ids: set[uuid.UUID] = set()
            for raw_dataset_id in dataset_ids:
                try:
                    dataset_uuid = uuid.UUID(str(raw_dataset_id))
                except ValueError as exc:
                    raise ValueError(f"Invalid dataset_id: {raw_dataset_id}") from exc
                if dataset_uuid in seen_dataset_ids:
                    continue
                dataset = self.repo.get_dataset(dataset_uuid)
                if dataset is None:
                    raise ValueError(f"Dataset not found: {raw_dataset_id}")
                if dataset.collection_id != voice_profile.collection_id:
                    raise ValueError("Selected dataset does not belong to the same collection as the voice profile")
                selected_datasets.append(dataset)
                seen_dataset_ids.add(dataset_uuid)

            if not selected_datasets:
                raise ValueError("At least one dataset must be selected")

            entries: list[dict[str, Any]] = []
            for dataset in selected_datasets:
                rows = self.repo.list_dataset_entries(dataset.dataset_id)
                for entry in rows:
                    entries.append(
                        {
                            "entry_id": str(entry.entry_id),
                            "dataset_id": str(entry.dataset_id),
                            "dataset_name": dataset.dataset_name,
                            "entry_type": entry.entry_type,
                            "text_clean": entry.text_clean,
                            "blob_uri": entry.blob_uri,
                            "metadata_asset": entry.metadata_asset,
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

            for dataset in selected_datasets:
                self.repo.add_version_dataset(
                    voice_profile_version_id=version.voice_profile_version_id,
                    dataset=dataset,
                    sample_size=dataset.entry_count,
                )

            voice_profile.updated_at = version.updated_at
            self.db.add(voice_profile)
            self.db.commit()
            version = self.repo.activate_version(version.voice_profile_version_id)
            self.db.refresh(voice_profile)
            return voice_profile, version
        except Exception:
            self.db.rollback()
            raise
