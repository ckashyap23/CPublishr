from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode


class TopicInitializationNode(OrchestrationNode):
    name = "topic_initialization"

    def __init__(self, llm: AzureOpenAIClient | None = None):
        self.llm = llm

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        p = context.input_payload
        title = (p.get("topic_title") or "").strip()
        normalized = title.lower()

        if self.llm and self.llm.enabled and title:
            try:
                raw = self.llm.chat(
                    system_prompt="Normalize topics for content workflows. Return strict JSON.",
                    user_prompt=(
                        "Return JSON with key `normalized_topic` only. "
                        f"topic_title={title!r}"
                    ),
                )
                parsed = parse_json_object(raw)
                candidate = (parsed.get("normalized_topic") or "").strip()
                if candidate:
                    normalized = candidate
            except Exception:
                pass

        bundle = {
            "topic_title": title,
            "normalized_topic": normalized,
            "core_idea": (p.get("core_idea") or "").strip(),
            "target_audience": p.get("target_audience"),
            "content_depth": p.get("content_depth"),
            "tone_preference": p.get("tone_preference"),
            "distribution_targets": p.get("distribution_targets") or [],
        }
        context.state["context_bundle"] = bundle
        return NodeExecutionResult(
            status="completed",
            output_payload={"project_id": context.project_id, "normalized_topic": normalized, "context_bundle": bundle},
        )
