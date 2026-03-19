"""Artifact Style Suggestion Service
=====================================
Given a project's context (topic title, core idea, master content) and a list of
selected image/video formats, calls the LLM once per media kind (image / video) and
returns pre-filled style suggestions: theme, subject_prompt, and all style enum fields.

The caller (API endpoint) passes the result directly to the UI as default values.
All fields remain editable by the user before generation.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.services.llm.client import chat, is_enabled, parse_json_object

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Format → kind mapping (only media formats need suggestions)
# ---------------------------------------------------------------------------
_FORMAT_KIND: dict[str, str] = {
    "post_image": "image",
    "thumbnail": "image",
    "banner": "image",
    "cover": "image",
    "gif": "video",
    "reel": "video",
    "short_video": "video",
}

_FORMAT_LABELS: dict[str, str] = {
    "post_image": "social media post image (square 1:1)",
    "thumbnail": "video or article thumbnail (wide 16:9)",
    "banner": "website or social media banner (panoramic wide)",
    "cover": "profile or publication cover (portrait)",
    "gif": "short looping animated GIF",
    "reel": "vertical short-form video reel (9:16, TikTok/Instagram Reels)",
    "short_video": "short narrative video (15–60 seconds)",
}

# ---------------------------------------------------------------------------
# Valid enum values per kind (mirrors orchestrator validation)
# ---------------------------------------------------------------------------
_IMAGE_ENUMS: dict[str, set[str]] = {
    "mood": {"playful", "serious", "premium", "cozy", "dramatic", "energetic"},
    "medium": {
        "photo", "illustration", "3d_render", "comic",
        "watercolor", "oil_paint", "vector_flat", "pixel_art",
    },
    "texture": {"clean", "film_grain", "halftone", "paper", "canvas", "noise"},
    "palette_mode": {"brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"},
    "focus_negative_space": {
        "subject_centered", "rule_of_thirds",
        "negative_space_left", "negative_space_right",
    },
}

_VIDEO_ENUMS: dict[str, set[str]] = {
    "mood": {
        "playful", "serious", "premium", "cozy", "dramatic", "energetic",
        "inspiring", "suspenseful", "mysterious", "whimsical", "futuristic", "nostalgic",
    },
    "lighting": {
        "soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused",
        "studio_softbox", "high_key_bright", "low_key_moody", "neon_night",
        "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight",
    },
    "palette_mode": {"brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"},
}

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_IMAGE_STYLE_FIELDS = """\
Return a JSON object with exactly these keys:
  "theme"               – concise visual mood/theme phrase (max 150 chars)
  "subject_prompt"      – the main visual subject or scene description (max 300 chars)
  "mood"                – one of: playful, serious, premium, cozy, dramatic, energetic
  "medium"              – one of: photo, illustration, 3d_render, comic, watercolor, oil_paint, vector_flat, pixel_art
  "texture"             – one of: clean, film_grain, halftone, paper, canvas, noise
  "palette_mode"        – one of: brand, monochrome, pastel, neon, earthy, muted, high_contrast
  "focus_negative_space"– one of: subject_centered, rule_of_thirds, negative_space_left, negative_space_right"""

_VIDEO_STYLE_FIELDS = """\
Return a JSON object with exactly these keys:
  "theme"          – concise visual mood/theme phrase (max 150 chars)
  "subject_prompt" – the main visual subject or scene description (max 300 chars)
  "mood"           – one of: playful, serious, premium, cozy, dramatic, energetic, inspiring, suspenseful, mysterious, whimsical, futuristic, nostalgic
  "lighting"       – one of: soft_daylight, golden_hour, sunset_warm, overcast_diffused, studio_softbox, high_key_bright, low_key_moody, neon_night, backlit_silhouette, rim_light, volumetric_godrays, dramatic_spotlight
  "palette_mode"   – one of: brand, monochrome, pastel, neon, earthy, muted, high_contrast"""


def _build_prompts(
    kind: str,
    formats: list[str],
    topic_title: str,
    core_idea: str,
    master_body: str,
) -> tuple[str, str]:
    format_labels = "; ".join(
        _FORMAT_LABELS.get(f, f) for f in formats
    )
    style_fields = _IMAGE_STYLE_FIELDS if kind == "image" else _VIDEO_STYLE_FIELDS

    system_prompt = (
        f"You are a creative director specializing in {kind} content for social media and digital marketing. "
        "Given a piece of content, suggest the most effective visual style settings for AI media generation. "
        "Be specific, creative, and directly informed by the content's topic and tone. "
        "Respond ONLY with a valid JSON object — no markdown, no explanation, no prose."
    )

    content_snippet = (master_body or "").strip()[:2500]
    user_prompt = (
        f"Topic: {topic_title}\n"
        f"Core idea: {core_idea}\n\n"
        f"Master content:\n{content_snippet}\n\n"
        f"Target format(s): {format_labels}\n\n"
        f"Suggest the best visual style settings for generating these {kind} assets.\n\n"
        f"{style_fields}\n\n"
        "Output only the JSON object."
    )

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_text(raw: dict[str, Any], key: str, max_len: int) -> str | None:
    val = str(raw.get(key) or "").strip()[:max_len]
    return val if val else None


def _validate_enum(raw: dict[str, Any], key: str, allowed: set[str]) -> str | None:
    val = str(raw.get(key) or "").strip().lower()
    return val if val in allowed else None


def _validate_image(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    theme = _validate_text(raw, "theme", 150)
    if theme:
        out["theme"] = theme
    subject = _validate_text(raw, "subject_prompt", 300)
    if subject:
        out["subject_prompt"] = subject
    for key, allowed in _IMAGE_ENUMS.items():
        val = _validate_enum(raw, key, allowed)
        if val:
            out[key] = val
    return out


def _validate_video(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    theme = _validate_text(raw, "theme", 150)
    if theme:
        out["theme"] = theme
    subject = _validate_text(raw, "subject_prompt", 300)
    if subject:
        out["subject_prompt"] = subject
    for key, allowed in _VIDEO_ENUMS.items():
        val = _validate_enum(raw, key, allowed)
        if val:
            out[key] = val
    return out


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ArtifactSuggestionService:
    """Generates LLM-powered style suggestions for image and video artifact formats."""

    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self.projects = ProjectRepository(db, user_id=user_id)
        self.contents = ContentRepository(db, user_id=user_id)
        

    def suggest(
        self,
        *,
        project_id: str,
        formats: list[str],
    ) -> dict[str, dict[str, Any]]:
        """
        Returns per-kind suggestions keyed by "image" and/or "video".

        Example response:
          {
            "image": { "theme": "...", "subject_prompt": "...", "mood": "premium", ... },
            "video": { "theme": "...", "subject_prompt": "...", "mood": "inspiring", ... }
          }

        Only kinds present among the requested formats are included.
        Returns an empty dict if no media formats are requested or if LLM is not configured.
        """
        if not is_enabled():
            logger.warning("LLM not configured — skipping artifact suggestions")
            return {}

        # Group formats by kind
        kinds_to_formats: dict[str, list[str]] = {}
        for fmt in formats:
            kind = _FORMAT_KIND.get(fmt)
            if kind:
                kinds_to_formats.setdefault(kind, []).append(fmt)

        if not kinds_to_formats:
            return {}

        # Fetch project context
        bundle = self.projects.get_context_bundle(project_id) or {}
        final_version = self.contents.get_latest_final_version(project_id)
        source = final_version or self.contents.get_latest_version(project_id)
        master_body = (source.content if source else "") or ""
        topic_title = str(bundle.get("topic_title") or "").strip()
        core_idea = str(bundle.get("core_idea") or "").strip()

        if not topic_title and not master_body:
            logger.warning(
                "No project context found for project_id=%s — returning empty suggestions",
                project_id,
            )
            return {}

        results: dict[str, dict[str, Any]] = {}

        for kind, kind_formats in kinds_to_formats.items():
            try:
                system_prompt, user_prompt = _build_prompts(
                    kind=kind,
                    formats=kind_formats,
                    topic_title=topic_title,
                    core_idea=core_idea,
                    master_body=master_body,
                )
                raw_text = chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.6,
                    max_tokens=450,
                )
                raw = parse_json_object(raw_text)
                validated = _validate_image(raw) if kind == "image" else _validate_video(raw)
                if validated:
                    results[kind] = validated
                    logger.info(
                        "Generated %s style suggestion for project=%s formats=%s",
                        kind, project_id, kind_formats,
                    )
            except Exception:
                logger.exception(
                    "Suggestion LLM call failed for kind=%s project=%s", kind, project_id
                )
                # Continue — return whatever succeeded for other kinds

        return results
