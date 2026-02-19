from __future__ import annotations

from typing import Any

KIND_BY_FORMAT: dict[str, str] = {
    # text
    "caption": "text",
    "x_post": "text",
    "x_thread": "text",
    "blog_short": "text",
    "blog_long": "text",
    "newsletter": "text",
    "script_short": "text",
    "script_long": "text",
    "hook_bank": "text",
    "headline_variants": "text",
    "cta_variants": "text",
    "faq": "text",
    "playbook": "text",
    # image
    "image_prompt_pack": "image",
    "thumbnail_prompt": "image",
    "cover_prompt": "image",
    "carousel_prompt_pack": "image",
    "image": "image",
    "thumbnail": "image",
    "cover": "image",
    # video
    "storyboard": "video",
    "shotlist": "video",
    "edit_decision_list": "video",
    "subtitle_srt": "video",
    "video": "video",
    # audio
    "voiceover_script": "audio",
    "voiceover_audio": "audio",
    # gif
    "gif_storyboard": "gif",
    "gif_loop": "gif",
    # bundle
    "bundle": "bundle",
}

ALLOWED_FORMATS = set(KIND_BY_FORMAT.keys())
ALLOWED_KINDS = {"text", "image", "video", "audio", "gif", "bundle"}


def derive_kind(fmt: str) -> str:
    normalized = (fmt or "").strip()
    if normalized not in KIND_BY_FORMAT:
        raise ValueError(f"Unsupported format: {normalized}")
    return KIND_BY_FORMAT[normalized]


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
