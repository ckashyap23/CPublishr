from __future__ import annotations

from typing import Any


class TTSProvider:
    """Placeholder TTS provider. Replace with real speech synthesis integration."""

    def generate(self, *, text: str, settings: dict[str, Any] | None = None) -> str:
        token = abs(hash((text[:200], str(settings or {})))) % 10_000_000
        return f"mock://audio/voice_{token}.mp3"