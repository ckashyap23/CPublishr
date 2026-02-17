from __future__ import annotations

from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode


class GenerateArtifactsNode(OrchestrationNode):
    name = "generate_artifacts"

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        master_document = str(context.state.get("final_master_document") or "").strip()
        topic = str((context.state.get("context_bundle") or {}).get("topic_title") or "Master Content").strip()
        if not master_document:
            master_document = "# Finalized content\n\nnot specified"

        artifacts = [
            {
                "artifact_type": "reel",
                "title": f"{topic} - Reel Script",
                "content": "\n".join(master_document.splitlines()[:12]).strip() or "not specified",
                "metadata": {"duration_sec": 45, "format": "vertical"},
            },
            {
                "artifact_type": "short_video",
                "title": f"{topic} - Short Video Outline",
                "content": "\n".join(master_document.splitlines()[:18]).strip() or "not specified",
                "metadata": {"duration_sec": 90, "format": "horizontal"},
            },
            {
                "artifact_type": "voice_over_clip",
                "title": f"{topic} - Voice Over",
                "content": master_document[:1600] if master_document else "not specified",
                "metadata": {"voice_style": "neutral", "language": "en-US"},
            },
            {
                "artifact_type": "text_blog",
                "title": f"{topic} - Blog Draft",
                "content": master_document,
                "metadata": {"format": "markdown"},
            },
        ]
        return NodeExecutionResult(status="completed", output_payload={"artifacts": artifacts})
