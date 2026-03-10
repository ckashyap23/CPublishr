from sqlalchemy.orm import Session
import json
from typing import Any
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.parse import urlparse as _urlparse
from string import ascii_uppercase

from src.contracts.prd import DistributionRequest, DistributionResponse
from src.core.config import settings
from src.db.repositories.artifact_repository import ArtifactRepository
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.db.repositories.publish_repository import PublishRepository
from src.platforms.adapters.registry import get_adapter, get_platform_field_schema, list_platforms
from src.schemas.publishing_schemas import (
    ArtifactPublishRequest,
    ArtifactPublishJobResponse,
    SaveToPublishRequest,
    SaveToPublishResponse,
)
from src.services.storage.artifact_blob_storage import generate_read_url
from src.utils.ids import new_id


class PublishingService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.projects = ProjectRepository(db, user_id=user_id)
        self.content = ContentRepository(db, user_id=user_id)
        self.artifacts = ArtifactRepository(db, user_id=user_id)
        self.publish = PublishRepository(db, user_id=user_id)

    @staticmethod
    def _payload_json(row) -> dict:
        raw = getattr(row, "payload_snapshot", None)
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw) if raw else {}
            except Exception:
                return {}
        return {}

    @staticmethod
    def _slug(value: str, fallback: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return fallback
        slug = re.sub(r"[^\w\-]+", "_", raw).strip("_")
        return slug or fallback

    @staticmethod
    def _join_prefix(*parts: str) -> str:
        cleaned = [str(p).strip().strip("/") for p in parts if str(p).strip()]
        return "/".join(cleaned)

    @staticmethod
    def _validate_output_root(output_root: str) -> None:
        raw = str(output_root or "").strip()
        if not raw:
            return
        lowered = raw.lower()
        if lowered.startswith(("azure://", "az://", "gs://", "file://")):
            return
        parsed = urlparse(raw)
        scheme = str(parsed.scheme or "").strip().lower()
        if scheme in {"http", "https"}:
            raise ValueError(
                "HTTP/HTTPS publish destinations are not directly writable. "
                "Use azure://, gs://, file://, or a local absolute path."
            )

    def _resolve_save_publish_path_parts(
        self, *, project_id: str, platform: str, user_name: str
    ) -> tuple[str, str, str, str]:
        user_slug = self._slug(self.user_id, "user")
        project_slug = self._slug(project_id, "project")
        platform_slug = self._slug(platform.lower(), "platform")
        user_name_slug = self._slug(user_name, "user")
        leaf = f"{platform_slug}_{user_name_slug}"
        relative = self._join_prefix("Publishr", user_slug, project_slug, leaf)
        return user_slug, project_slug, leaf, relative

    def _save_to_local_output_path(self, *, root: str, relative: str) -> str:
        base = root.strip()
        if base.lower().startswith("file://"):
            parsed = urlparse(base)
            base = parsed.path or ""
            if parsed.netloc:
                base = f"//{parsed.netloc}{base}"
            if re.match(r"^/[A-Za-z]:", base):
                base = base[1:]
        target = Path(base) / Path(relative)
        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    def _save_to_azure_output_path(self, *, root: str, relative: str) -> str:
        try:
            from azure.storage.blob import BlobServiceClient
        except Exception as exc:
            raise ValueError("azure-storage-blob is not installed in this environment.") from exc

        conn = str(settings.azure_storage_connection_string or "").strip()
        if not conn:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required for azure:// OUTPUT_PATH.")

        parsed = urlparse(root)
        scheme = parsed.scheme.lower()
        if scheme not in {"azure", "az"}:
            raise ValueError("Invalid Azure output path scheme. Use azure:// or az://")
        container = (parsed.netloc or "").strip()
        if not container:
            raise ValueError("Azure OUTPUT_PATH must include a container, e.g. azure://artifacts/base-prefix")
        prefix = (parsed.path or "").strip().strip("/")
        blob_prefix = self._join_prefix(prefix, relative)
        marker_blob = self._join_prefix(blob_prefix, ".keep")

        svc = BlobServiceClient.from_connection_string(conn)
        container_client = svc.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass
        container_client.upload_blob(marker_blob, b"", overwrite=True)
        account_url = svc.url.rstrip("/")
        return f"{account_url}/{container}/{blob_prefix}"

    def _save_to_gcs_output_path(self, *, root: str, relative: str) -> str:
        try:
            from google.cloud import storage  # type: ignore
        except Exception as exc:
            raise ValueError("google-cloud-storage is not installed in this environment.") from exc

        parsed = urlparse(root)
        if parsed.scheme.lower() != "gs":
            raise ValueError("Invalid GCS output path. Use gs://<bucket>/<prefix>")
        bucket = (parsed.netloc or "").strip()
        if not bucket:
            raise ValueError("GCS OUTPUT_PATH must include a bucket, e.g. gs://my-bucket/base-prefix")
        prefix = (parsed.path or "").strip().strip("/")
        blob_prefix = self._join_prefix(prefix, relative)
        marker_blob = self._join_prefix(blob_prefix, ".keep")

        client = storage.Client()
        bucket_ref = client.bucket(bucket)
        bucket_ref.blob(marker_blob).upload_from_string(b"")
        return f"gs://{bucket}/{blob_prefix}"

    def save_to_publish(self, payload: SaveToPublishRequest) -> SaveToPublishResponse:
        SaveToPublishRequest.model_validate(payload)
        project_id = str(payload.project_id or "").strip()
        platform = str(payload.platform or "").strip().lower()
        user_name = str(payload.user_name or "").strip()
        if not project_id:
            raise ValueError("project_id is required")
        if not platform:
            raise ValueError("platform is required")
        if not user_name:
            raise ValueError("user_name is required")

        self.projects.get_or_create(project_id)
        adapter, fields, field_mapping_entities, mapping_snapshot = self._resolve_field_mappings(
            project_id=project_id,
            platform=platform,
            field_mappings=list(payload.field_mappings or []),
        )
        platform_payload = adapter.build_platform_payload(field_mapping=field_mapping_entities)

        output_root = str(payload.output_path or "").strip() or str(settings.output_path or "").strip()
        if not output_root:
            raise ValueError("OUTPUT_PATH is not configured. Set OUTPUT_PATH in backend/.env")
        self._validate_output_root(output_root)

        _, _, _, relative = self._resolve_save_publish_path_parts(
            project_id=project_id,
            platform=platform,
            user_name=user_name,
        )

        lower = output_root.lower()
        if hasattr(adapter, "save_to_publish_bundle"):
            adapter.save_to_publish_bundle(
                payload=platform_payload,
                output_root=output_root,
                relative_path=relative,
            )
            if lower.startswith("azure://") or lower.startswith("az://"):
                created = self._save_to_azure_output_path(root=output_root, relative=relative)
            elif lower.startswith("gs://"):
                created = self._save_to_gcs_output_path(root=output_root, relative=relative)
            else:
                created = self._save_to_local_output_path(root=output_root, relative=relative)
        else:
            if lower.startswith("azure://") or lower.startswith("az://"):
                created = self._save_to_azure_output_path(root=output_root, relative=relative)
            elif lower.startswith("gs://"):
                created = self._save_to_gcs_output_path(root=output_root, relative=relative)
            else:
                created = self._save_to_local_output_path(root=output_root, relative=relative)

        job_id = new_id("pub")
        self.publish.create_job(
            publish_job_id=job_id,
            project_id=project_id,
            platform=platform,
            status="saved",
            scheduled_time=None,
            external_id=None,
            platform_output_id=None,
            payload_snapshot={
                "project_id": project_id,
                "platform": platform,
                "mode": "save_to_publish",
                "field_mappings": mapping_snapshot,
                "platform_fields": fields,
                "resolved_payload": platform_payload,
                "output_path": created,
            },
        )

        return SaveToPublishResponse(
            status="saved",
            project_id=project_id,
            platform=platform,
            user_name=user_name,
            output_path=created,
        )

    def browse_output_locations(self, path: str | None = None) -> dict[str, Any]:
        raw = str(path or "").strip()
        if not raw:
            dirs = [f"{d}:\\" for d in ascii_uppercase if Path(f"{d}:\\").exists()]
            return {
                "current_path": "",
                "parent_path": None,
                "directories": dirs,
            }

        parsed = raw
        if parsed.lower().startswith("file://"):
            p = urlparse(parsed).path or ""
            if re.match(r"^/[A-Za-z]:", p):
                p = p[1:]
            parsed = p

        current = Path(parsed)
        if not current.exists() or not current.is_dir():
            raise ValueError(f"Path is not a directory: {raw}")

        children = []
        try:
            for item in current.iterdir():
                if item.is_dir():
                    children.append(str(item))
        except Exception as exc:
            raise ValueError(f"Unable to browse directory: {raw}. {exc}") from exc

        children.sort(key=lambda x: x.lower())
        parent = str(current.parent) if current.parent != current else None
        return {
            "current_path": str(current),
            "parent_path": parent,
            "directories": children,
        }

    def pick_local_output_path(self, start_path: str | None = None) -> str | None:
        """
        Open native OS folder picker on the backend host machine.
        Returns selected absolute path or None if cancelled.
        """
        try:
            import tkinter as tk  # type: ignore
            from tkinter import filedialog  # type: ignore
        except Exception as exc:
            raise ValueError("Native local folder picker is unavailable (tkinter not installed).") from exc

        initial_dir = str(start_path or "").strip()
        if initial_dir.lower().startswith("file://"):
            parsed = urlparse(initial_dir)
            initial_dir = parsed.path or ""
            if re.match(r"^/[A-Za-z]:", initial_dir):
                initial_dir = initial_dir[1:]

        if initial_dir and not Path(initial_dir).exists():
            initial_dir = ""

        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        try:
            selected = filedialog.askdirectory(
                parent=root,
                initialdir=initial_dir or None,
                title="Select output folder",
                mustexist=False,
            )
        finally:
            try:
                root.destroy()
            except Exception:
                pass

        selected = str(selected or "").strip()
        return selected or None

    def list_available_platforms(self) -> list[str]:
        return list_platforms()

    def get_platform_field_schema(self, platform: str) -> dict:
        return get_platform_field_schema(platform)

    @staticmethod
    def _refresh_sas_urls_in_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Refresh expired Azure Blob SAS URLs in payload_json.assets.

        This matters because artifact payloads stored in DB may contain URIs with SAS query params
        that expire; publishing adapters (e.g., LinkedIn) may fetch bytes from these URIs later.
        """
        if not isinstance(payload, dict):
            return payload
        out = dict(payload)
        assets = out.get("assets", [])
        if not isinstance(assets, list):
            return out

        refreshed: list[Any] = []
        default_container = (settings.azure_artifacts_container or "artifacts").strip() or "artifacts"

        for asset in assets:
            if not isinstance(asset, dict):
                refreshed.append(asset)
                continue

            a = dict(asset)
            blob_path = a.get("blob_path")
            uri = a.get("uri")

            # Preferred: regenerate from stored blob_path.
            if isinstance(blob_path, str) and blob_path.strip():
                new_uri = generate_read_url(default_container, blob_path.strip())
                if new_uri:
                    a["uri"] = new_uri
                refreshed.append(a)
                continue

            # Fallback: extract container + blob path from existing URI.
            if isinstance(uri, str) and "blob.core.windows.net" in uri:
                try:
                    parsed = _urlparse(uri)
                    # path is: /<container>/<blob_path...>
                    parts = (parsed.path or "").strip("/").split("/", 1)
                    if len(parts) == 2:
                        container_name, extracted_blob_path = parts[0].strip(), parts[1].strip()
                        if container_name and extracted_blob_path:
                            new_uri = generate_read_url(container_name, extracted_blob_path)
                            if new_uri:
                                a["uri"] = new_uri
                                a["blob_path"] = extracted_blob_path
                except Exception:
                    pass

            refreshed.append(a)

        out["assets"] = refreshed
        return out

    def _artifact_entity_for_mapping(self, artifact) -> dict:
        payload = artifact.payload_json or {}
        if isinstance(payload, dict):
            payload = self._refresh_sas_urls_in_payload(payload)
        return {
            "artifact_id": artifact.artifact_id,
            "project_id": artifact.project_id,
            "format": artifact.format,
            "kind": artifact.kind,
            "title": artifact.title,
            "payload_json": payload,
            "tags_json": artifact.tags_json or [],
            "status": artifact.status,
            "revision": artifact.revision,
        }

    @staticmethod
    def _normalize_mapping_order(value: Any, *, fallback: int) -> int:
        try:
            if value is None:
                return fallback
            return int(value)
        except Exception:
            return fallback

    def _load_project_artifacts_index(self, project_id: str) -> dict[str, object]:
        rows = self.artifacts.list_artifacts(project_id)
        return {a.artifact_id: a for a in rows}

    def _resolve_field_mappings(
        self,
        *,
        project_id: str,
        platform: str,
        field_mappings: list[Any],
    ) -> tuple[Any, list[dict], dict[str, list[dict]], list[dict]]:
        adapter = get_adapter(platform)
        if adapter is None:
            raise ValueError(f"Unsupported platform adapter: {platform}")

        schema = adapter.get_field_schema()
        fields = schema.get("fields") if isinstance(schema, dict) else None
        if not isinstance(fields, list):
            raise ValueError(f"Adapter field schema invalid for platform '{platform}'")

        field_defs: dict[str, dict] = {}
        for field in fields:
            if not isinstance(field, dict):
                continue
            key = str(field.get("field_key") or "").strip()
            if key:
                field_defs[key] = field

        artifact_index = self._load_project_artifacts_index(project_id)
        field_mapping_entities: dict[str, list[dict]] = {}
        mapping_snapshot: list[dict] = []

        for item in field_mappings or []:
            field_key = str(item.field_key or "").strip()
            if not field_key:
                continue
            if field_key not in field_defs:
                raise ValueError(f"Unknown platform field '{field_key}' for platform '{platform}'")
            field_def = field_defs[field_key]
            accepted_formats = {
                str(x).strip()
                for x in (field_def.get("accepted_artifact_formats") or [])
                if str(x).strip()
            }
            sources = list(item.sources or [])

            resolved_sources: list[dict] = []
            for idx, source in enumerate(sources):
                artifact_id = str(source.artifact_id or "").strip()
                part = str(source.part or "").strip()
                render_as = str(source.render_as).strip() if source.render_as is not None else None
                order = self._normalize_mapping_order(source.order, fallback=idx)
                if not artifact_id:
                    raise ValueError(f"Field '{field_key}' has a source with missing artifact_id")
                if not part:
                    raise ValueError(f"Field '{field_key}' has a source with missing part")
                row = artifact_index.get(artifact_id)
                if row is None:
                    raise ValueError(f"Artifact '{artifact_id}' not found in project '{project_id}'")
                if accepted_formats and row.format not in accepted_formats:
                    raise ValueError(
                        f"Artifact '{artifact_id}' format '{row.format}' not allowed for field '{field_key}'"
                    )
                resolved_sources.append(
                    {
                        "artifact_id": artifact_id,
                        "part": part,
                        "render_as": render_as,
                        "order": order,
                        "artifact": self._artifact_entity_for_mapping(row),
                    }
                )

            resolved_sources.sort(key=lambda x: int(x.get("order") or 0))
            field_mapping_entities[field_key] = resolved_sources
            mapping_snapshot.append(
                {
                    "field_key": field_key,
                    "sources": [
                        {
                            "artifact_id": s["artifact_id"],
                            "part": s["part"],
                            "render_as": s.get("render_as"),
                            "order": s.get("order"),
                        }
                        for s in resolved_sources
                    ],
                }
            )

        for field_key, field_def in field_defs.items():
            if not bool(field_def.get("required")):
                continue
            if not field_mapping_entities.get(field_key):
                raise ValueError(f"Required field '{field_key}' is not mapped")

        return adapter, fields, field_mapping_entities, mapping_snapshot

    def create_artifact_publish_job(self, payload: ArtifactPublishRequest) -> ArtifactPublishJobResponse:
        ArtifactPublishRequest.model_validate(payload)
        project_id = str(payload.project_id or "").strip()
        platform = str(payload.platform or "").strip().lower()
        if not project_id:
            raise ValueError("project_id is required")
        if not platform:
            raise ValueError("platform is required")

        self.projects.get_or_create(project_id)
        adapter, fields, field_mapping_entities, mapping_snapshot = self._resolve_field_mappings(
            project_id=project_id,
            platform=platform,
            field_mappings=list(payload.field_mappings or []),
        )

        platform_payload = adapter.build_platform_payload(field_mapping=field_mapping_entities)
        publish_result = adapter.publish(payload=platform_payload)
        status = str((publish_result or {}).get("status") or "published").strip() or "published"

        job_id = new_id("pub")
        row = self.publish.create_job(
            publish_job_id=job_id,
            project_id=project_id,
            platform=platform,
            status=status,
            scheduled_time=None,
            external_id=(publish_result or {}).get("external_id"),
            platform_output_id=None,
            payload_snapshot={
                "project_id": project_id,
                "platform": platform,
                "field_mappings": mapping_snapshot,
                "platform_fields": fields,
                "resolved_payload": platform_payload,
                "publish_result": publish_result or {},
            },
        )

        return ArtifactPublishJobResponse(
            publish_job_id=row.publish_job_id,
            project_id=row.project_id,
            platform=row.platform,
            status=row.status,
            external_id=row.external_id,
            external_url=(publish_result or {}).get("external_url"),
            scheduled_time=(row.scheduled_time.isoformat() if row.scheduled_time else None),
            payload_snapshot=self._payload_json(row),
        )

    def create_job(self, payload: DistributionRequest) -> DistributionResponse:
        DistributionRequest.model_validate(payload)
        project_id = (payload.content_payload or {}).get("project_id")
        if not isinstance(project_id, str) or not project_id:
            raise ValueError("content_payload.project_id is required")
        self.projects.get_or_create(project_id)

        latest_output = self.content.get_latest_platform_output(project_id, payload.platform)
        if latest_output is None:
            raise ValueError(f"No generated platform output found for project '{project_id}' and platform '{payload.platform}'")

        external_id = new_id("ext")
        self.publish.create_job(
            publish_job_id=new_id("pub"),
            project_id=project_id,
            platform=payload.platform,
            status="published",
            scheduled_time=None,
            external_id=external_id,
            platform_output_id=latest_output.output_id,
            payload_snapshot={
                "project_id": project_id,
                "platform": payload.platform,
                "platform_output_id": latest_output.output_id,
                "format_type": latest_output.format_type,
                "content": latest_output.content,
            },
        )
        return DistributionResponse(status="published", external_id=external_id)
