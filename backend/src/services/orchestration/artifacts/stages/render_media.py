from __future__ import annotations

from src.services.media.image_provider import ImageProvider
from src.services.media.tts_provider import TTSProvider
from src.services.media.video_provider import VideoProvider
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext, StageResult


class RenderMediaStage:
    name = "render_media"

    def __init__(self, image_provider: ImageProvider | None = None, video_provider: VideoProvider | None = None, tts_provider: TTSProvider | None = None):
        self.image_provider = image_provider or ImageProvider()
        self.video_provider = video_provider or VideoProvider()
        self.tts_provider = tts_provider or TTSProvider()

    def run(self, ctx: PipelineContext) -> StageResult:
        drafts: list[ArtifactDraft] = []

        prompt_packs = ctx.stage_outputs.get("prompt_pack") or []

        if "image" in ctx.requested_formats:
            image_prompts = [d for d in prompt_packs if d.format == "image_prompt_pack"]
            payload = default_payload_template()
            for pack in image_prompts:
                for item in (pack.payload_json.get("items") or []):
                    uri = self.image_provider.generate(prompt=str(item.get("text") or "image prompt"), settings=pack.payload_json.get("settings") or {})
                    payload["assets"].append(
                        {
                            "asset_id": None,
                            "role": str(item.get("title") or "image"),
                            "uri": uri,
                            "mime_type": "image/png",
                            "width": None,
                            "height": None,
                            "duration_sec": None,
                            "size_bytes": None,
                            "checksum": None,
                            "meta": {},
                        }
                    )
            drafts.append(ArtifactDraft(format="image", title=f"{ctx.topic_title} - Rendered Images", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        if "voiceover_audio" in ctx.requested_formats:
            text_anchor = ctx.master_body[:2000] if ctx.master_body else "not specified"
            uri = self.tts_provider.generate(text=text_anchor, settings={"language": "en"})
            payload = default_payload_template()
            payload["assets"] = [
                {
                    "asset_id": None,
                    "role": "primary",
                    "uri": uri,
                    "mime_type": "audio/mpeg",
                    "width": None,
                    "height": None,
                    "duration_sec": None,
                    "size_bytes": None,
                    "checksum": None,
                    "meta": {},
                }
            ]
            drafts.append(ArtifactDraft(format="voiceover_audio", title=f"{ctx.topic_title} - Voiceover Audio", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        if "video" in ctx.requested_formats:
            storyboards = [d for d in prompt_packs if d.format == "storyboard"]
            payload = default_payload_template()
            for board in storyboards:
                for scene in (board.payload_json.get("items") or []):
                    uri = self.video_provider.generate(
                        prompt=str(scene.get("prompt") or "scene"),
                        duration_sec=float(scene.get("timing_sec") or 3.0),
                        settings=board.payload_json.get("settings") or {},
                    )
                    payload["assets"].append(
                        {
                            "asset_id": None,
                            "role": "preview",
                            "uri": uri,
                            "mime_type": "video/mp4",
                            "width": None,
                            "height": None,
                            "duration_sec": scene.get("timing_sec"),
                            "size_bytes": None,
                            "checksum": None,
                            "meta": {"sequence": scene.get("sequence")},
                        }
                    )
            drafts.append(ArtifactDraft(format="video", title=f"{ctx.topic_title} - Video Preview Clips", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        return StageResult(stage=self.name, drafts=drafts)