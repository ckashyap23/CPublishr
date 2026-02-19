from __future__ import annotations

from typing import Any


class FfmpegService:
    """Placeholder ffmpeg assembler. Replace with real ffmpeg pipeline."""

    def assemble_video(self, *, scene_assets: list[str], audio_uri: str | None = None, settings: dict[str, Any] | None = None) -> str:
        token = abs(hash((tuple(scene_assets), audio_uri, str(settings or {})))) % 10_000_000
        return f"mock://video/final_{token}.mp4"

    def assemble_gif(self, *, frame_assets: list[str], settings: dict[str, Any] | None = None) -> str:
        token = abs(hash((tuple(frame_assets), str(settings or {})))) % 10_000_000
        return f"mock://gif/final_{token}.gif"