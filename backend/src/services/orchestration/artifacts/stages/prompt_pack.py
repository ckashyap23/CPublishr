from __future__ import annotations

from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext, StageResult


class PromptPackStage:
    name = "prompt_pack"

    def run(self, ctx: PipelineContext) -> StageResult:
        drafts: list[ArtifactDraft] = []

        if "image_prompt_pack" in ctx.requested_formats:
            payload = default_payload_template()
            payload["items"] = [
                {"item_type": "prompt", "sequence": 1, "title": "cover", "text": "Create cover image"},
                {"item_type": "prompt", "sequence": 2, "title": "thumbnail", "text": "Create thumbnail image"},
            ]
            payload["settings"] = {
                "style": ctx.style_settings.get("style", "clean editorial"),
                "aspect_ratio": ctx.style_settings.get("aspect_ratio", "1:1"),
            }
            drafts.append(ArtifactDraft(format="image_prompt_pack", title=f"{ctx.topic_title} - Image Prompt Pack", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        if "storyboard" in ctx.requested_formats:
            payload = default_payload_template()
            payload["items"] = [
                {"item_type": "scene", "sequence": 1, "text": "Narration line 1", "prompt": "Scene prompt 1", "timing_sec": 3.0},
                {"item_type": "scene", "sequence": 2, "text": "Narration line 2", "prompt": "Scene prompt 2", "timing_sec": 4.0},
            ]
            payload["settings"] = {
                "aspect_ratio": ctx.style_settings.get("aspect_ratio", "9:16"),
                "target_duration_sec": ctx.style_settings.get("target_duration_sec", 30),
            }
            drafts.append(ArtifactDraft(format="storyboard", title=f"{ctx.topic_title} - Storyboard", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        if "gif_storyboard" in ctx.requested_formats:
            payload = default_payload_template()
            payload["items"] = [
                {"item_type": "frame", "sequence": 1, "prompt": "Frame prompt 1", "timing_sec": 0.4},
                {"item_type": "frame", "sequence": 2, "prompt": "Frame prompt 2", "timing_sec": 0.4},
            ]
            payload["settings"] = {"loop": True, "fps": 12}
            drafts.append(ArtifactDraft(format="gif_storyboard", title=f"{ctx.topic_title} - GIF Storyboard", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        return StageResult(stage=self.name, drafts=drafts)