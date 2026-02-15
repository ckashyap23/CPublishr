from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode


class ResearchTrendsNode(OrchestrationNode):
    name = "research_trends"

    def __init__(self, llm: AzureOpenAIClient | None = None):
        self.llm = llm

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        b = context.state.get("context_bundle") or {}
        topic = (b.get("normalized_topic") or "ai").strip()

        fallback = {
            "research_summary": f"Research summary for {topic}.",
            "emerging_tools": ["agents", "vector-db", "orchestrators"],
            "recent_discussions": ["quality vs speed", "human-in-loop"],
            "key_insights": ["master document reduces drift"],
            "contrarian_angles": ["more agents is not always better"],
        }

        output = fallback
        if self.llm and self.llm.enabled:
            try:
                raw = self.llm.chat(
                    system_prompt="You are a research assistant. Return strict JSON only.",
                    user_prompt=(
                        "Return JSON with keys: research_summary (string), emerging_tools (string[]), "
                        "recent_discussions (string[]), key_insights (string[]), contrarian_angles (string[]). "
                        f"Topic: {topic}. Keep concise."
                    ),
                )
                parsed = parse_json_object(raw)
                if parsed:
                    output = {
                        "research_summary": str(parsed.get("research_summary") or fallback["research_summary"]),
                        "emerging_tools": [str(x) for x in (parsed.get("emerging_tools") or fallback["emerging_tools"])],
                        "recent_discussions": [str(x) for x in (parsed.get("recent_discussions") or fallback["recent_discussions"])],
                        "key_insights": [str(x) for x in (parsed.get("key_insights") or fallback["key_insights"])],
                        "contrarian_angles": [str(x) for x in (parsed.get("contrarian_angles") or fallback["contrarian_angles"])],
                    }
            except Exception:
                output = fallback

        context.state["research"] = output
        return NodeExecutionResult(status="completed", output_payload=output)
