from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from sqlalchemy.orm import Session

from src.db.repositories.artifact_repository import ArtifactRepository
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.services.orchestration.artifact_schema import allowed_formats, normalize_payload, validate_payload_shape
from src.services.orchestration.artifacts.contracts import ArtifactDraft, GenerationOptions, PipelineContext
from src.services.orchestration.artifacts.formats.registry import resolve_builder
from src.utils.ids import new_id


class ArtifactPipelineOrchestrator:
    """Per-format artifact generation pipeline (no stage fan-out)."""

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.projects = ProjectRepository(db, user_id=user_id)
        self.contents = ContentRepository(db, user_id=user_id)
        self.artifacts = ArtifactRepository(db, user_id=user_id)

    @staticmethod
    def _merge_tags(seed_keywords: list[str], payload: dict[str, Any], existing: list[str] | None = None) -> list[str]:
        acc: list[str] = []
        for source in [seed_keywords, payload.get("keywords") or [], existing or []]:
            for item in source:
                s = str(item).strip()
                if s and s not in acc:
                    acc.append(s)
        return acc

    @staticmethod
    def _style_settings_for_format(
        fmt: str,
        *,
        shared: dict[str, Any] | None = None,
        by_format: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        if isinstance(shared, dict):
            merged.update(shared)
        if isinstance(by_format, dict):
            fmt_settings = by_format.get(fmt)
            if isinstance(fmt_settings, dict):
                merged.update(fmt_settings)
        return merged

    def _build_context(
        self,
        *,
        project_id: str,
        requested_formats: list[str],
        style_settings: dict[str, Any] | None = None,
    ) -> PipelineContext:
        bundle = self.projects.get_context_bundle(project_id) or {}
        final_version = self.contents.get_latest_final_version(project_id)
        source = final_version or self.contents.get_latest_version(project_id)
        master_body = source.content if source else "not specified"
        seed_keywords = self.contents.decode_keywords(source) if source else []
        topic_title = str(bundle.get("topic_title") or "Master Content")
        core_idea = str(bundle.get("core_idea") or "")
        supported = allowed_formats()
        invalid_formats = [f for f in requested_formats if f not in supported]
        if invalid_formats:
            raise ValueError(f"Unsupported format(s): {', '.join(sorted(set(invalid_formats)))}")
        normalized_formats = [f for f in requested_formats if f in supported]

        return PipelineContext(
            user_id=self.user_id,
            project_id=project_id,
            context_bundle=bundle,
            topic_title=topic_title,
            core_idea=core_idea,
            master_body=master_body,
            seed_keywords=seed_keywords,
            target_audience=bundle.get("target_audience"),
            audience_familiarity=bundle.get("audience_familiarity"),
            detail_level=bundle.get("detail_level"),
            tone_preference=bundle.get("tone_preference"),
            requested_formats=normalized_formats,
            style_settings=style_settings or {},
        )

    def _persist_draft(self, *, project_id: str, draft: ArtifactDraft, revision_mode: str) -> dict[str, Any]:
        payload = normalize_payload(draft.payload_json)
        validate_payload_shape(draft.format, payload)
        tags = self._merge_tags([], payload, draft.tags_json)

        if revision_mode == "reset":
            row = self.artifacts.create_artifact(
                artifact_id=new_id("art"),
                project_id=project_id,
                format=draft.format,
                title=draft.title,
                payload_json=payload,
                tags_json=tags,
                status=draft.status,
                revision=max(1, int(draft.revision or 1)),
                parent_artifact_id=draft.parent_artifact_id,
            )
        else:
            row = self.artifacts.create_next_revision(
                artifact_id=new_id("art"),
                project_id=project_id,
                format=draft.format,
                title=draft.title,
                payload_json=payload,
                tags_json=tags,
                status=draft.status,
            )

        return {
            "artifact_id": row.artifact_id,
            "project_id": row.project_id,
            "format": row.format,
            "kind": row.kind,
            "title": row.title,
            "payload_json": row.payload_json or {},
            "tags_json": row.tags_json or [],
            "status": row.status,
            "revision": row.revision,
            "parent_artifact_id": row.parent_artifact_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def generate(
        self,
        *,
        project_id: str,
        requested_formats: list[str],
        options: GenerationOptions | None = None,
        style_settings: dict[str, Any] | None = None,
        style_settings_by_format: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        opts = options or GenerationOptions()
        self.projects.get_or_create(project_id)
        ctx = self._build_context(project_id=project_id, requested_formats=requested_formats, style_settings=style_settings)

        if opts.revision_mode == "reset":
            self.artifacts.delete_artifacts_for_project(project_id)

        persisted: list[dict[str, Any]] = []
        for fmt in ctx.requested_formats:
            builder = resolve_builder(fmt)
            if builder is None:
                raise ValueError(f"No format builder registered for: {fmt}")
            fmt_ctx = replace(
                ctx,
                style_settings=self._style_settings_for_format(
                    fmt,
                    shared=style_settings,
                    by_format=style_settings_by_format,
                ),
            )
            draft = builder.build(fmt=fmt, ctx=fmt_ctx)
            persisted.append(self._persist_draft(project_id=project_id, draft=draft, revision_mode=opts.revision_mode))

        return {
            "project_id": project_id,
            "requested_formats": list(requested_formats),
            "options": asdict(opts),
            "artifacts": persisted,
        }
