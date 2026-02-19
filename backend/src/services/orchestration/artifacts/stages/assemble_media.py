from __future__ import annotations

from src.services.media.ffmpeg_service import FfmpegService
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext, StageResult


class AssembleMediaStage:
    name = "assemble"

    def __init__(self, ffmpeg: FfmpegService | None = None):
        self.ffmpeg = ffmpeg or FfmpegService()

    def run(self, ctx: PipelineContext) -> StageResult:
        drafts: list[ArtifactDraft] = []
        rendered = ctx.stage_outputs.get("render_media") or []
        prompt_packs = ctx.stage_outputs.get("prompt_pack") or []

        if "video" in ctx.requested_formats:
            scene_assets: list[str] = []
            audio_uri: str | None = None
            for draft in rendered:
                if draft.format == "video":
                    for asset in (draft.payload_json.get("assets") or []):
                        if asset.get("uri"):
                            scene_assets.append(str(asset["uri"]))
                if draft.format == "voiceover_audio":
                    assets = draft.payload_json.get("assets") or []
                    if assets:
                        audio_uri = str(assets[0].get("uri") or "") or None
            if scene_assets:
                uri = self.ffmpeg.assemble_video(scene_assets=scene_assets, audio_uri=audio_uri, settings={"aspect_ratio": "9:16"})
                payload = default_payload_template()
                payload["assets"] = [{"role": "primary", "uri": uri, "mime_type": "video/mp4", "duration_sec": None, "meta": {}}]
                drafts.append(ArtifactDraft(format="video", title=f"{ctx.topic_title} - Assembled Video", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        if "gif_loop" in ctx.requested_formats:
            boards = [d for d in prompt_packs if d.format == "gif_storyboard"]
            if boards:
                frame_assets = [f"mock://frame/{i}.png" for i in range(1, len((boards[0].payload_json.get('items') or [])) + 1)]
                uri = self.ffmpeg.assemble_gif(frame_assets=frame_assets, settings=boards[0].payload_json.get("settings") or {})
                payload = default_payload_template()
                payload["assets"] = [{"role": "primary", "uri": uri, "mime_type": "image/gif", "duration_sec": None, "meta": {}}]
                drafts.append(ArtifactDraft(format="gif_loop", title=f"{ctx.topic_title} - GIF Loop", payload_json=payload, tags_json=list(ctx.seed_keywords)))

        return StageResult(stage=self.name, drafts=drafts)