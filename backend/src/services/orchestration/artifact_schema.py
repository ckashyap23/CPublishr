from __future__ import annotations

from typing import Any

def kind_by_format_map() -> dict[str, str]:
    from src.services.orchestration.artifacts.formats.registry import get_kind_by_format

    return get_kind_by_format()


def formats_by_kind_map() -> dict[str, list[str]]:
    from src.services.orchestration.artifacts.formats.registry import get_formats_by_kind

    return get_formats_by_kind()


def allowed_formats() -> set[str]:
    return set(kind_by_format_map().keys())


def derive_kind(fmt: str) -> str:
    normalized = (fmt or "").strip()
    kinds = kind_by_format_map()
    if normalized not in kinds:
        raise ValueError(f"Unsupported format: {normalized}")
    return kinds[normalized]


def default_payload_template() -> dict[str, Any]:
    return {
        "version": "1.0",
        "body": None,
        "items": [],
        "assets": [],
        "prompts": [],
        "settings": {},
        "notes": None,
    }


def normalize_payload(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    template = default_payload_template()
    src = payload or {}
    out = {
        "version": str(src.get("version") or template["version"]),
        "body": src.get("body"),
        "items": src.get("items") if isinstance(src.get("items"), list) else [],
        "assets": src.get("assets") if isinstance(src.get("assets"), list) else [],
        "prompts": src.get("prompts") if isinstance(src.get("prompts"), list) else [],
        "settings": src.get("settings") if isinstance(src.get("settings"), dict) else {},
        "notes": src.get("notes"),
    }
    # Keep optional keys except redundant fields that must stay at artifact level.
    for key in src.keys():
        if key in {"keywords", "tags_json"}:
            continue
        if key not in out:
            out[key] = src[key]
    # Defensive cleanup for callers that may still include deprecated payload fields.
    out.pop("keywords", None)
    out.pop("tags_json", None)
    return out


def validate_payload_shape(fmt: str, payload: dict[str, Any]) -> None:
    normalized = normalize_payload(payload)
    text_body_formats = {"caption", "x_post", "blog_short", "blog_long", "newsletter"}
    if fmt in text_body_formats and not isinstance(normalized.get("body"), (str, type(None))):
        raise ValueError(f"Invalid payload.body for format={fmt}")
    if fmt == "x_thread":
        items = normalized.get("items") or []
        if not items:
            raise ValueError("x_thread requires payload.items")
    if fmt in {"storyboard", "gif_storyboard"}:
        items = normalized.get("items") or []
        if not items:
            raise ValueError(f"{fmt} requires payload.items")
