from __future__ import annotations

import importlib
import pkgutil
from functools import lru_cache

from src.services.orchestration.artifacts.formats.base import ArtifactFormatBuilder, RegisteredBuilder

PACKAGE = "src.services.orchestration.artifacts.formats"
ALLOWED_KINDS = {"text", "image", "video", "audio", "gif", "bundle"}


def _iter_modules() -> list[str]:
    pkg = importlib.import_module(PACKAGE)
    modules: list[str] = []
    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name.startswith("_") or mod.name in {"base", "registry"}:
            continue
        modules.append(f"{PACKAGE}.{mod.name}")
    return modules


@lru_cache(maxsize=1)
def discover_builders() -> list[RegisteredBuilder]:
    rows: list[RegisteredBuilder] = []
    for module_name in _iter_modules():
        module = importlib.import_module(module_name)
        builder = getattr(module, "BUILDER", None)
        if builder is None:
            continue
        formats = getattr(builder, "formats", set())
        if not isinstance(formats, set) or not formats:
            raise ValueError(f"Builder formats must be non-empty set in {module_name}")
        format_kinds = getattr(builder, "format_kinds", None)
        if format_kinds is None:
            kind = str(getattr(builder, "kind", "")).strip()
            if kind not in ALLOWED_KINDS:
                raise ValueError(f"Invalid builder kind in {module_name}: {kind}")
        else:
            if not isinstance(format_kinds, dict):
                raise ValueError(f"format_kinds must be a dict in {module_name}")
            for fmt in formats:
                k = str(format_kinds.get(fmt, "")).strip()
                if k not in ALLOWED_KINDS:
                    raise ValueError(f"Invalid kind '{k}' for format '{fmt}' in {module_name}")
        rows.append(RegisteredBuilder(module_name=module_name, builder=builder))
    return rows


@lru_cache(maxsize=1)
def format_builder_map() -> dict[str, ArtifactFormatBuilder]:
    out: dict[str, ArtifactFormatBuilder] = {}
    for row in discover_builders():
        for fmt in row.builder.formats:
            key = str(fmt).strip()
            if not key:
                continue
            if key in out:
                raise ValueError(f"Duplicate artifact format registration: {key}")
            out[key] = row.builder
    return out


def resolve_builder(fmt: str) -> ArtifactFormatBuilder | None:
    return format_builder_map().get((fmt or "").strip())


def get_kind_by_format() -> dict[str, str]:
    out: dict[str, str] = {}
    for fmt, builder in format_builder_map().items():
        format_kinds = getattr(builder, "format_kinds", None)
        if isinstance(format_kinds, dict):
            out[fmt] = str(format_kinds[fmt]).strip()
        else:
            out[fmt] = str(getattr(builder, "kind", "")).strip()
    return out


def get_formats_by_kind() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {k: [] for k in ALLOWED_KINDS}
    for fmt, kind in get_kind_by_format().items():
        out.setdefault(kind, []).append(fmt)
    for kind in out.keys():
        out[kind] = sorted(out[kind])
    return out
