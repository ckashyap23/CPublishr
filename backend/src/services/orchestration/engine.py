import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from src.contracts.prd import (
    EditorialRequest,
    EditorialResponse,
    MasterContentResponse,
    ResearchTrendResponse,
    TopicInitializationRequest,
    TopicInitializationResponse,
)
from src.db.repositories.artifact_repository import ArtifactRepository
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.editorial_session_repository import EditorialSessionRepository
from src.db.repositories.project_repository import ProjectRepository
from src.services.llm.azure_openai import AzureOpenAIClient
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.editorial import EditorialNode
from src.services.orchestration.nodes.generate_artifacts import GenerateArtifactsNode
from src.services.orchestration.nodes.master_content import MasterContentNode
from src.services.orchestration.nodes.research_trends import ResearchTrendsNode
from src.services.orchestration.nodes.topic_initialization import TopicInitializationNode
from src.services.platforms.registry import default_platform_registry
from src.utils.ids import new_id

logger = logging.getLogger(__name__)


class OrchestrationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.content = ContentRepository(db)
        self.artifacts = ArtifactRepository(db)
        self.editorial_sessions = EditorialSessionRepository(db)
        self.platform_registry = default_platform_registry()
        self.llm = AzureOpenAIClient()

        self.node0 = TopicInitializationNode(self.llm)
        self.node1 = ResearchTrendsNode(self.llm)
        self.node2 = MasterContentNode(self.llm)
        self.node3 = EditorialNode(self.llm)
        self.node4 = GenerateArtifactsNode()

    @staticmethod
    def _inherit_variant_label_from_source(source) -> str | None:
        if source.version_kind in {"variant", "editorial"}:
            return source.variant_label
        return None

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        return NodeExecutionResult(status="completed", output_payload=context.state)

    def run_default_flow(self, payload: TopicInitializationRequest) -> tuple[str, str]:
        TopicInitializationRequest.model_validate(payload)
        self.projects.get_or_create(payload.project_id)

        run_id = new_id("run")
        ctx = NodeExecutionContext(project_id=payload.project_id, run_id=run_id, input_payload=payload.model_dump())

        n0 = self.node0.run(ctx)
        TopicInitializationResponse.model_validate(n0.output_payload)
        self.projects.set_context_bundle(payload.project_id, n0.output_payload.get("context_bundle") or {})

        n1 = self.node1.run(ctx)
        ResearchTrendResponse.model_validate(n1.output_payload)

        n2 = self.node2.run(ctx)
        MasterContentResponse.model_validate(n2.output_payload)

        master_doc = n2.output_payload["master_document"]
        base_outline = [str(x) for x in (n2.output_payload.get("structure_outline") or [])]
        base_keywords = [str(x) for x in (n2.output_payload.get("core_arguments") or [])]
        base_version = self.content.create_version(
            version_id=new_id("ver"),
            project_id=payload.project_id,
            content=master_doc,
            version_number=self.content.next_version_number(payload.project_id),
            version_kind="base",
            variant_label=None,
            keywords=base_keywords,
            structure_outline=base_outline,
            version_stage="draft",
            source_version_number=None,
        )
        for mv in n2.output_payload.get("master_variants") or []:
            variant_doc = str(mv.get("master_document") or "").strip()
            if not variant_doc:
                continue
            variant_label = str(mv.get("label") or "").strip() or None
            variant_outline = [str(x) for x in (mv.get("structure_outline") or [])]
            variant_keywords = [str(x) for x in (mv.get("core_arguments") or base_keywords)]
            self.content.create_version(
                version_id=new_id("ver"),
                project_id=payload.project_id,
                content=variant_doc,
                version_number=self.content.next_version_number(payload.project_id),
                version_kind="variant",
                variant_label=variant_label,
                keywords=variant_keywords,
                structure_outline=variant_outline,
                version_stage="draft",
                source_version_number=base_version.version_number,
            )
        return run_id, "awaiting_editorial"

    def _run_post_editorial_pipeline(self, project_id: str, master_doc: str) -> None:
        bundle = self.projects.get_context_bundle(project_id) or {}
        ctx = NodeExecutionContext(
            project_id=project_id,
            run_id=new_id("run"),
            input_payload={"project_id": project_id},
            state={"context_bundle": bundle, "final_master_document": master_doc},
        )
        artifacts_payload = self.node4.run(ctx).output_payload
        self.artifacts.delete_artifacts_for_project(project_id)
        for item in artifacts_payload.get("artifacts") or []:
            try:
                self.artifacts.create_artifact(
                    artifact_id=new_id("art"),
                    project_id=project_id,
                    artifact_type=str(item.get("artifact_type") or "text_blog"),
                    title=str(item.get("title") or "Untitled Artifact"),
                    content=str(item.get("content") or ""),
                    metadata=item.get("metadata") or {},
                )
            except Exception:
                logger.exception("Failed to persist artifact for project_id=%s", project_id)

        # Regenerate platform outputs from finalized editorial content.
        self.content.delete_platform_outputs_for_project(project_id)
        for target in bundle.get("distribution_targets") or []:
            adapter = self.platform_registry.get(target)
            if adapter is None:
                continue
            out = adapter.transform(master_doc, bundle | {"artifacts_generated": True})
            self.content.create_platform_output(
                output_id=new_id("out"),
                project_id=project_id,
                platform=target,
                format_type="default",
                content=json.dumps(out, ensure_ascii=False),
                optimized=True,
            )

    def generate_artifacts_from_latest_editorial(self, project_id: str) -> None:
        project = self.projects.get(project_id)
        latest_editorial = None
        if project and project.final_version_number is not None:
            latest_editorial = self.content.get_version_by_number(project_id, int(project.final_version_number))
        if latest_editorial is None:
            latest_editorial = self.content.get_latest_final_version(project_id)
        if latest_editorial is None:
            latest_editorial = self.content.get_latest_version_by_kind(project_id, "editorial")
        if latest_editorial is None:
            raise ValueError("No finalized editorial version found for project")
        self._run_post_editorial_pipeline(project_id, latest_editorial.content)

    def run_editorial(self, payload: EditorialRequest) -> EditorialResponse:
        EditorialRequest.model_validate(payload)
        current = self.content.get_version_by_number(payload.project_id, payload.current_version)
        if current is None:
            raise ValueError("Requested content version not found")

        ctx = NodeExecutionContext(
            project_id=payload.project_id,
            run_id=new_id("run"),
            input_payload=payload.model_dump(),
            state={"current_master_document": current.content},
        )
        res = self.node3.run(ctx)
        validated = EditorialResponse.model_validate(res.output_payload)
        next_version = self.content.next_version_number(payload.project_id)
        inherited_variant_label = self._inherit_variant_label_from_source(current)
        source_outline = self.content.decode_structure_outline(current)
        source_keywords = self.content.decode_keywords(current)

        self.content.clear_final_stage(payload.project_id)
        self.content.create_version(
            version_id=new_id("ver"),
            project_id=payload.project_id,
            content=validated.updated_master_document,
            version_number=next_version,
            version_kind="editorial",
            variant_label=inherited_variant_label,
            keywords=source_keywords,
            structure_outline=source_outline,
            version_stage="final",
            source_version_number=current.version_number,
        )
        self.projects.set_final_version(payload.project_id, next_version)
        self._run_post_editorial_pipeline(payload.project_id, validated.updated_master_document)
        return EditorialResponse(
            draft_version=next_version,
            updated_master_document=validated.updated_master_document,
            change_log=validated.change_log,
        )

    def finalize_version_direct(self, *, project_id: str, current_version: int) -> EditorialResponse:
        current = self.content.get_version_by_number(project_id, current_version)
        if current is None:
            raise ValueError("Requested content version not found")
        next_version = self.content.next_version_number(project_id)
        inherited_variant_label = self._inherit_variant_label_from_source(current)
        source_outline = self.content.decode_structure_outline(current)
        source_keywords = self.content.decode_keywords(current)
        self.content.clear_final_stage(project_id)
        self.content.create_version(
            version_id=new_id("ver"),
            project_id=project_id,
            content=current.content,
            version_number=next_version,
            version_kind="editorial",
            variant_label=inherited_variant_label,
            keywords=source_keywords,
            structure_outline=source_outline,
            version_stage="final",
            source_version_number=current.version_number,
        )
        self.projects.set_final_version(project_id, next_version)
        self._run_post_editorial_pipeline(project_id, current.content)
        return EditorialResponse(
            draft_version=next_version,
            updated_master_document=current.content,
            change_log=["finalized_direct_without_iteration"],
        )

    def start_editorial_session(self, *, project_id: str, current_version: int, user_comment: str) -> tuple[str, EditorialResponse, int]:
        current = self.content.get_version_by_number(project_id, current_version)
        if current is None:
            raise ValueError("Requested content version not found")

        payload = EditorialRequest(
            project_id=project_id,
            current_version=current_version,
            editor_actions=[{"action": "rewrite", "target_section": "document"}],
            user_feedback=user_comment,
        )
        ctx = NodeExecutionContext(
            project_id=project_id,
            run_id=new_id("run"),
            input_payload=payload.model_dump(),
            state={"current_master_document": current.content},
        )
        res = EditorialResponse.model_validate(self.node3.run(ctx).output_payload)

        session_id = new_id("edit")
        self.editorial_sessions.create(
            session_id=session_id,
            project_id=project_id,
            base_version=current_version,
            working_content=res.updated_master_document,
        )
        return session_id, res, 1

    def iterate_editorial_session(self, *, session_id: str, user_comment: str) -> tuple[EditorialResponse, int]:
        session = self.editorial_sessions.get(session_id)
        if session is None:
            raise ValueError("Editorial session not found")
        if session.finalized:
            raise ValueError("Editorial session already finalized")

        payload = EditorialRequest(
            project_id=session.project_id,
            current_version=session.base_version + int(session.current_iteration) - 1,
            editor_actions=[{"action": "rewrite", "target_section": "document"}],
            user_feedback=user_comment,
        )
        ctx = NodeExecutionContext(
            project_id=session.project_id,
            run_id=new_id("run"),
            input_payload=payload.model_dump(),
            state={"current_master_document": session.working_content},
        )
        res = EditorialResponse.model_validate(self.node3.run(ctx).output_payload)

        updated = self.editorial_sessions.update_iteration(session_id=session_id, working_content=res.updated_master_document)
        return res, int(updated.current_iteration)

    def finalize_editorial_session(self, *, session_id: str) -> EditorialResponse:
        session = self.editorial_sessions.get(session_id)
        if session is None:
            raise ValueError("Editorial session not found")
        if session.finalized:
            raise ValueError("Editorial session already finalized")

        source = self.content.get_version_by_number(session.project_id, int(session.base_version))
        if source is None:
            raise ValueError("Source content version for editorial session not found")
        inherited_variant_label = self._inherit_variant_label_from_source(source)
        source_outline = self.content.decode_structure_outline(source)
        source_keywords = self.content.decode_keywords(source)

        next_version = self.content.next_version_number(session.project_id)
        self.content.clear_final_stage(session.project_id)
        self.content.create_version(
            version_id=new_id("ver"),
            project_id=session.project_id,
            content=session.working_content,
            version_number=next_version,
            version_kind="editorial",
            variant_label=inherited_variant_label,
            keywords=source_keywords,
            structure_outline=source_outline,
            version_stage="final",
            source_version_number=source.version_number,
        )
        self.projects.set_final_version(session.project_id, next_version)
        self.editorial_sessions.finalize(session_id)
        self._run_post_editorial_pipeline(session.project_id, session.working_content)

        return EditorialResponse(
            draft_version=next_version,
            updated_master_document=session.working_content,
            change_log=["finalized_from_session"],
        )

    def regenerate_outline_draft(self, *, project_id: str, source_version: int, structure_outline: list[str]) -> dict[str, Any]:
        source = self.content.get_version_by_number(project_id, source_version)
        if source is None:
            raise ValueError("Requested source content version not found")
        cleaned_outline = [str(x).strip() for x in (structure_outline or []) if str(x).strip()]
        if not cleaned_outline:
            raise ValueError("structure_outline must contain at least one section")

        preview = source.content
        if self.llm and self.llm.enabled:
            prompt = (
                "Rewrite the markdown content to align with this section order while preserving meaning and facts.\n"
                "Return only markdown.\n\n"
                f"Target outline: {cleaned_outline}\n\n"
                f"Original content:\n{source.content}"
            )
            preview = self.llm.chat(
                system_prompt="You are a careful editorial assistant.",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=2500,
            )

        inherited_variant_label = self._inherit_variant_label_from_source(source)
        next_version = self.content.next_version_number(project_id)
        created = self.content.create_version(
            version_id=new_id("ver"),
            project_id=project_id,
            content=(preview or source.content).strip(),
            version_number=next_version,
            version_kind="editorial",
            variant_label=inherited_variant_label,
            keywords=self.content.decode_keywords(source),
            structure_outline=cleaned_outline,
            version_stage="draft",
            source_version_number=source.version_number,
        )
        return {
            "project_id": project_id,
            "source_version": source_version,
            "draft_version": created.version_number,
            "content": created.content,
            "version_kind": created.version_kind,
            "variant_label": created.variant_label,
            "version_stage": created.version_stage,
        }

    def save_inline_draft(
        self,
        *,
        project_id: str,
        source_version: int,
        content: str,
        version_label: str | None = None,
    ) -> dict[str, Any]:
        source = self.content.get_version_by_number(project_id, source_version)
        if source is None:
            raise ValueError("Requested source content version not found")
        if not (content or "").strip():
            raise ValueError("content cannot be empty")
        inherited_variant_label = self._inherit_variant_label_from_source(source)
        resolved_variant_label = (version_label or "").strip() or inherited_variant_label
        next_version = self.content.next_version_number(project_id)
        created = self.content.create_version(
            version_id=new_id("ver"),
            project_id=project_id,
            content=content.strip(),
            version_number=next_version,
            version_kind="editorial",
            variant_label=resolved_variant_label,
            keywords=self.content.decode_keywords(source),
            structure_outline=self.content.decode_structure_outline(source),
            version_stage="draft",
            source_version_number=source.version_number,
        )
        return {
            "project_id": project_id,
            "source_version": source_version,
            "draft_version": created.version_number,
            "content": created.content,
            "version_kind": created.version_kind,
            "variant_label": created.variant_label,
            "version_stage": created.version_stage,
        }

    def feedback_preview(self, *, project_id: str, source_version: int, user_feedback: str) -> dict[str, Any]:
        source = self.content.get_version_by_number(project_id, source_version)
        if source is None:
            raise ValueError("Requested source content version not found")
        payload = EditorialRequest(
            project_id=project_id,
            current_version=source_version,
            editor_actions=[{"action": "rewrite", "target_section": "document"}],
            user_feedback=user_feedback,
        )
        ctx = NodeExecutionContext(
            project_id=project_id,
            run_id=new_id("run"),
            input_payload=payload.model_dump(),
            state={"current_master_document": source.content},
        )
        res = EditorialResponse.model_validate(self.node3.run(ctx).output_payload)
        return {
            "project_id": project_id,
            "source_version": source_version,
            "preview_content": res.updated_master_document,
            "change_log": res.change_log,
        }

    def finalize_selected_version(self, *, project_id: str, selected_version: int) -> dict[str, Any]:
        selected = self.content.get_version_by_number(project_id, selected_version)
        if selected is None:
            raise ValueError("Requested selected content version not found")
        self.content.clear_final_stage(project_id)
        updated = self.content.set_version_stage(project_id, selected_version, "final")
        if updated is None:
            raise ValueError("Failed to mark selected content version as final")
        self.projects.set_final_version(project_id, selected_version)
        self._run_post_editorial_pipeline(project_id, updated.content)
        return {"project_id": project_id, "final_version": selected_version, "status": "editorial_finalized"}
