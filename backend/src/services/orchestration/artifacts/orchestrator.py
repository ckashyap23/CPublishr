from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from src.db.repositories.artifact_repository import ArtifactRepository
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.services.orchestration.artifact_schema import ALLOWED_FORMATS, normalize_payload, validate_payload_shape
from src.services.orchestration.artifacts.contracts import ArtifactDraft, GenerationOptions, PipelineContext
from src.services.orchestration.artifacts.stages.assemble_media import AssembleMediaStage
from src.services.orchestration.artifacts.stages.package_bundle import PackageBundleStage
from src.services.orchestration.artifacts.stages.plan_text import PlanTextStage
from src.services.orchestration.artifacts.stages.prompt_pack import PromptPackStage
from src.services.orchestration.artifacts.stages.render_media import RenderMediaStage
from src.utils.ids import new_id


class ArtifactPipelineOrchestrator:
    """Multi-stage artifact generation pipeline with placeholder stage implementations."""

    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.contents = ContentRepository(db)
        self.artifacts = ArtifactRepository(db)
        self.stage_plan = PlanTextStage()
        self.stage_prompt = PromptPackStage()
        self.stage_render = RenderMediaStage()
        self.stage_assemble = AssembleMediaStage()
        self.stage_package = PackageBundleStage()

    @staticmethod
    def _merge_tags(seed_keywords: list[str], payload: dict[str, Any], existing: list[str] | None = None) -> list[str]:
        acc: list[str] = []
        for source in [seed_keywords, payload.get("keywords") or [], existing or []]:
            for item in source:
                s = str(item).strip()
                if s and s not in acc:
                    acc.append(s)
        return acc

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
        master_body = (source.content if source else "not specified")
        seed_keywords = self.contents.decode_keywords(source) if source else []
        topic_title = str(bundle.get("topic_title") or "Master Content")
        core_idea = str(bundle.get("core_idea") or "")

        normalized_formats = [f for f in requested_formats if f in ALLOWED_FORMATS]
        return PipelineContext(
            project_id=project_id,
            topic_title=topic_title,
            core_idea=core_idea,
            master_body=master_body,
            seed_keywords=seed_keywords,
            target_audience=bundle.get("target_audience"),
            content_depth=bundle.get("content_depth"),
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
    ) -> dict[str, Any]:
        opts = options or GenerationOptions()
        # Ensure FK-safe writes even if caller invokes artifact generation
        # before explicit project initialization.
        self.projects.get_or_create(project_id)
        ctx = self._build_context(project_id=project_id, requested_formats=requested_formats, style_settings=style_settings)

        if opts.revision_mode == "reset":
            self.artifacts.delete_artifacts_for_project(project_id)

        if opts.run_plan:
            result = self.stage_plan.run(ctx)
            ctx.stage_outputs[result.stage] = result.drafts

        if opts.run_prompt_pack:
            result = self.stage_prompt.run(ctx)
            ctx.stage_outputs[result.stage] = result.drafts

        if opts.run_render_media:
            result = self.stage_render.run(ctx)
            ctx.stage_outputs[result.stage] = result.drafts

        if opts.run_assemble:
            result = self.stage_assemble.run(ctx)
            ctx.stage_outputs[result.stage] = result.drafts

        if opts.run_package:
            result = self.stage_package.run(ctx)
            ctx.stage_outputs[result.stage] = result.drafts

        all_drafts: list[ArtifactDraft] = []
        for stage_name in ["plan", "prompt_pack", "render_media", "assemble", "package"]:
            all_drafts.extend(ctx.stage_outputs.get(stage_name) or [])

        persisted = [self._persist_draft(project_id=project_id, draft=d, revision_mode=opts.revision_mode) for d in all_drafts]

        return {
            "project_id": project_id,
            "requested_formats": list(requested_formats),
            "stages": {
                "plan": opts.run_plan,
                "prompt_pack": opts.run_prompt_pack,
                "render_media": opts.run_render_media,
                "assemble": opts.run_assemble,
                "package": opts.run_package,
            },
            "options": asdict(opts),
            "artifacts": persisted,
        }
