import json

from sqlalchemy.orm import Session

from src.contracts.prd import (
    EditorialRequest,
    EditorialResponse,
    MasterContentResponse,
    ResearchTrendResponse,
    TopicInitializationRequest,
    TopicInitializationResponse,
)
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.editorial_session_repository import EditorialSessionRepository
from src.db.repositories.project_repository import ProjectRepository
from src.services.llm.azure_openai import AzureOpenAIClient
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.editorial import EditorialNode
from src.services.orchestration.nodes.master_content import MasterContentNode
from src.services.orchestration.nodes.research_trends import ResearchTrendsNode
from src.services.orchestration.nodes.topic_initialization import TopicInitializationNode
from src.services.platforms.registry import default_platform_registry
from src.utils.ids import new_id


class OrchestrationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.content = ContentRepository(db)
        self.editorial_sessions = EditorialSessionRepository(db)
        self.platform_registry = default_platform_registry()
        self.llm = AzureOpenAIClient()

        self.node0 = TopicInitializationNode(self.llm)
        self.node1 = ResearchTrendsNode(self.llm)
        self.node2 = MasterContentNode(self.llm)
        self.node3 = EditorialNode(self.llm)

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
        self.content.create_version(
            version_id=new_id("ver"),
            project_id=payload.project_id,
            content=master_doc,
            version_number=self.content.next_version_number(payload.project_id),
            version_kind="base",
            variant_label=None,
        )
        for mv in n2.output_payload.get("master_variants") or []:
            variant_doc = str(mv.get("master_document") or "").strip()
            if not variant_doc:
                continue
            variant_label = str(mv.get("label") or "").strip() or None
            self.content.create_version(
                version_id=new_id("ver"),
                project_id=payload.project_id,
                content=variant_doc,
                version_number=self.content.next_version_number(payload.project_id),
                version_kind="variant",
                variant_label=variant_label,
            )

        bundle = (n0.output_payload.get("context_bundle") or {}) | {
            "structure_outline": n2.output_payload.get("structure_outline") or [],
            "core_arguments": n2.output_payload.get("core_arguments") or [],
        }
        self.content.delete_platform_outputs_for_project(payload.project_id)
        for target in payload.distribution_targets or []:
            adapter = self.platform_registry.get(target)
            if adapter is None:
                continue
            out = adapter.transform(master_doc, bundle)
            self.content.create_platform_output(
                output_id=new_id("out"),
                project_id=payload.project_id,
                platform=target,
                format_type="default",
                content=json.dumps(out, ensure_ascii=False),
                optimized=True,
            )

        return run_id, "completed"

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
        inherited_variant_label = current.variant_label if current.version_kind == "variant" else None

        self.content.create_version(
            version_id=new_id("ver"),
            project_id=payload.project_id,
            content=validated.updated_master_document,
            version_number=next_version,
            version_kind="editorial",
            variant_label=inherited_variant_label,
        )
        return EditorialResponse(
            draft_version=next_version,
            updated_master_document=validated.updated_master_document,
            change_log=validated.change_log,
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

        next_version = self.content.next_version_number(session.project_id)
        self.content.create_version(
            version_id=new_id("ver"),
            project_id=session.project_id,
            content=session.working_content,
            version_number=next_version,
            version_kind="editorial",
            variant_label=None,
        )
        self.editorial_sessions.finalize(session_id)

        return EditorialResponse(
            draft_version=next_version,
            updated_master_document=session.working_content,
            change_log=["finalized_from_session"],
        )
