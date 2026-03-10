from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode
from src.services.storage.prompt_blob_storage import format_chat_prompt_text, save_prompt_text


class EditorialNode(OrchestrationNode):
    name = "editorial"

    def __init__(self, llm: AzureOpenAIClient | None = None):
        self.llm = llm

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        p = context.input_payload
        current_version = int(p.get("current_version") or 0)
        actions = p.get("editor_actions") or []
        feedback = (p.get("user_feedback") or "").strip()
        base_doc = (context.state.get("current_master_document") or "# Master document\n\n(placeholder)").strip()

        change_log: list[str] = []
        for action in actions:
            a = (action or {}).get("action")
            t = (action or {}).get("target_section")
            if a and t:
                change_log.append(f"{a} -> {t}")

        updated = (
            f"{base_doc}\n\n---\n"
            f"## Editorial update\n"
            f"Feedback: {feedback or '(none)'}\n"
            f"Actions:\n" + ("\n".join([f"- {c}" for c in change_log]) or "- (none)")
        ).strip()

        if self.llm and self.llm.enabled:
            try:
                system_prompt = "You are an editorial assistant. Return strict JSON only."
                user_prompt = (
                    "Return JSON with keys: updated_master_document (markdown), change_log (string[]). "
                    "Edit the document according to feedback and actions.\n"
                    f"feedback={feedback}\n"
                    f"actions={change_log}\n"
                    f"document=\n{base_doc}"
                )
                save_prompt_text(
                    user_id=str(context.state.get("user_id") or context.input_payload.get("user_id") or "user"),
                    project_id=str(context.project_id or context.input_payload.get("project_id") or "project"),
                    section="master-content",
                    name=f"editorial_v{current_version + 1}",
                    suffix="editorial",
                    text=format_chat_prompt_text(system_prompt=system_prompt, user_prompt=user_prompt),
                )
                raw = self.llm.chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.2,
                )
                parsed = parse_json_object(raw)
                if parsed:
                    updated = str(parsed.get("updated_master_document") or updated)
                    change_log = [str(x) for x in (parsed.get("change_log") or change_log)]
            except Exception:
                pass

        return NodeExecutionResult(
            status="completed",
            output_payload={
                "draft_version": current_version + 1,
                "updated_master_document": updated,
                "change_log": change_log,
            },
        )
