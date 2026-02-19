from __future__ import annotations

from typing import Any


class VideoProvider:
    """Placeholder video shot provider. Replace with real model integration."""

    def generate(self, *, prompt: str, duration_sec: float | None = None, settings: dict[str, Any] | None = None) -> str:
        token = abs(hash((prompt, duration_sec, str(settings or {})))) % 10_000_000
        return f"mock://video/clip_{token}.mp4"