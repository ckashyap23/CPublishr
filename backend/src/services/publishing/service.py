from sqlalchemy.orm import Session
import json
from typing import Any

from src.contracts.prd import DistributionRequest, DistributionResponse
from src.db.repositories.artifact_repository import ArtifactRepository
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.db.repositories.publish_repository import PublishRepository
from src.platforms.adapters.registry import get_adapter, get_platform_field_schema, list_platforms
from src.schemas.publishing_schemas import ArtifactPublishRequest, ArtifactPublishJobResponse
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

    def list_available_platforms(self) -> list[str]:
        return list_platforms()

    def get_platform_field_schema(self, platform: str) -> dict:
        return get_platform_field_schema(platform)

    def _artifact_entity_for_mapping(self, artifact) -> dict:
        return {
            "artifact_id": artifact.artifact_id,
            "project_id": artifact.project_id,
            "format": artifact.format,
            "kind": artifact.kind,
            "title": artifact.title,
            "payload_json": artifact.payload_json or {},
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

    def create_artifact_publish_job(self, payload: ArtifactPublishRequest) -> ArtifactPublishJobResponse:
        ArtifactPublishRequest.model_validate(payload)
        project_id = str(payload.project_id or "").strip()
        platform = str(payload.platform or "").strip().lower()
        if not project_id:
            raise ValueError("project_id is required")
        if not platform:
            raise ValueError("platform is required")

        self.projects.get_or_create(project_id)
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

        for item in payload.field_mappings or []:
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
