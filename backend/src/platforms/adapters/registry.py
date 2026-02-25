from __future__ import annotations

import importlib
import pkgutil
from functools import lru_cache
from typing import Any

PACKAGE = "src.platforms.adapters"


def _iter_modules() -> list[str]:
    pkg = importlib.import_module(PACKAGE)
    out: list[str] = []
    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name.startswith("_") or mod.name in {"base", "registry"}:
            continue
        out.append(f"{PACKAGE}.{mod.name}")
    return out


@lru_cache(maxsize=1)
def adapter_map() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for module_name in _iter_modules():
        module = importlib.import_module(module_name)
        adapter = getattr(module, "ADAPTER", None)
        if adapter is None:
            continue
        name = str(getattr(adapter, "platform_name", "") or "").strip().lower()
        if not name:
            continue
        if name in out:
            raise ValueError(f"Duplicate platform adapter registration: {name}")
        out[name] = adapter
    return out


def list_platforms() -> list[str]:
    return sorted(adapter_map().keys())


def get_adapter(platform: str) -> Any | None:
    return adapter_map().get(str(platform or "").strip().lower())


def get_platform_field_schema(platform: str) -> dict[str, Any]:
    adapter = get_adapter(platform)
    if adapter is None:
        raise ValueError(f"Unsupported platform adapter: {platform}")
    schema = adapter.get_field_schema()
    if not isinstance(schema, dict):
        raise ValueError(f"Adapter schema must be a dict for platform: {platform}")
    return schema


class PlatformRegistry:
    """Registry wrapper that provides a .get() method for backward compatibility."""

    def get(self, platform: str) -> Any | None:
        return get_adapter(platform)


def default_platform_registry() -> PlatformRegistry:
    """Return a default platform registry instance."""
    return PlatformRegistry()

