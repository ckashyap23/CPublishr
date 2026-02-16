from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode


class MasterContentNode(OrchestrationNode):
    name = "master_content"

    def __init__(self, llm: AzureOpenAIClient | None = None):
        self.llm = llm

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        b = context.state.get("context_bundle") or {}
        r = context.state.get("research") or {}
        title = (b.get("topic_title") or "AI Topic").strip()
        core = (b.get("core_idea") or "One idea, many platform formats.").strip()
        user_content = (b.get("user_content") or "").strip()
        user_section = f"## User Content Input\n{user_content}\n\n" if user_content else ""

        fallback_master = (
            f"# {title}\n\n"
            f"## Core Idea\n{core}\n\n"
            f"{user_section}"
            f"## Research\n{r.get('research_summary','')}\n\n"
            "## Framework\n"
            "1. Initialize topic\n2. Research\n3. Master doc\n4. Adapt per platform\n"
        ).strip()

        out = {
            "master_document": fallback_master,
            "structure_outline": ["Core idea", "Research", "Framework"],
            "core_arguments": ["same idea, different packaging"],
        }

        if self.llm and self.llm.enabled:
            try:
                raw = self.llm.chat(
                    system_prompt="You write canonical long-form content. Return strict JSON only.",
                    user_prompt=(
                        "Return JSON with keys: master_document (markdown), structure_outline (string[]), core_arguments (string[]). "
                        f"title={title}; core_idea={core}; user_content={user_content}; research_summary={r.get('research_summary','')}"
                    ),
                    temperature=0.4,
                )
                parsed = parse_json_object(raw)
                if parsed:
                    out = {
                        "master_document": str(parsed.get("master_document") or fallback_master),
                        "structure_outline": [str(x) for x in (parsed.get("structure_outline") or out["structure_outline"])],
                        "core_arguments": [str(x) for x in (parsed.get("core_arguments") or out["core_arguments"])],
                    }
            except Exception:
                pass

        context.state["master"] = out
        return NodeExecutionResult(status="completed", output_payload=out)
