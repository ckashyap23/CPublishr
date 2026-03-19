from src.services.llm.client import chat, is_enabled, parse_json_object
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode
from src.schemas.context_bundle import ContextBundle


class TopicInitializationNode(OrchestrationNode):
    name = "topic_initialization"

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        p = context.input_payload
        title = (p.get("topic_title") or "").strip()
        normalized = title.lower()

        if is_enabled() and title:
            try:
                raw = chat(
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

        raw_audience = p.get("target_audience")
        if isinstance(raw_audience, dict) and raw_audience.get("primary_segment"):
            target_audience = {
                "primary_segment": str(raw_audience.get("primary_segment")),
                "notes": (str(raw_audience.get("notes")).strip() if raw_audience.get("notes") is not None else None),
            }
        else:
            target_audience = {"primary_segment": "general", "notes": None}

        bundle = {
            "topic_title": title,
            "normalized_topic": normalized,
            "core_idea": (p.get("core_idea") or "").strip(),
            "user_content": (p.get("user_content") or "").strip() or None,
            "target_audience": target_audience,
            "audience_familiarity": p.get("audience_familiarity"),
            "detail_level": p.get("detail_level"),
            "tone_preference": p.get("tone_preference"),
            "stance": p.get("stance") or "balanced",
            "primary_goal": p.get("primary_goal"),
            "desired_action": p.get("desired_action"),
            "voice_profile_id": p.get("voice_profile_id"),
            "constraints": p.get("constraints"),
            "distribution_targets": p.get("distribution_targets"),
        }
        # Validate schema to prevent downstream breakages if keys/types drift.
        ContextBundle.model_validate(bundle)
        context.state["context_bundle"] = bundle
        return NodeExecutionResult(
            status="completed",
            output_payload={"project_id": context.project_id, "normalized_topic": normalized, "context_bundle": bundle},
        )
