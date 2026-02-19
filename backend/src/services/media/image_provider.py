from __future__ import annotations

from typing import Any


class ImageProvider:
    """Placeholder image provider. Replace with real model integration."""

    def generate(self, *, prompt: str, settings: dict[str, Any]) -> str:
        token = abs(hash((prompt, str(settings)))) % 10_000_000
        return f"mock://image/{token}.png"