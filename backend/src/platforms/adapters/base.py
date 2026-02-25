from __future__ import annotations

from typing import Any, Protocol


class PlatformAdapter(Protocol):
    platform_name: str

    def get_field_schema(self) -> dict[str, Any]: ...

    def build_platform_payload(self, *, field_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, Any]: ...

    def publish(self, *, payload: dict[str, Any]) -> dict[str, Any]: ...

