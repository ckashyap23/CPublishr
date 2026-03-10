from __future__ import annotations

import base64
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from src.core.config import settings
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext
from src.services.orchestration.artifacts.persistence import save_image_bytes_to_local, upload_artifact_bytes
from src.services.storage.artifact_blob_storage import blob_path_from_uri, download_bytes

logger = logging.getLogger(__name__)

DALLE_PROMPT_MAX_CHARS = 4000
FUTURE_IMAGE_EDIT_TOOL_NAMES = {"openai_edits", "stability_img2img"}


# =============================================================================
# Provider connector registry
# =============================================================================

def available_image_tools() -> dict[str, Callable[..., dict[str, Any]]]:
    """Return supported third-party image tool connectors."""
    return {
        "openai": connect_openai_images,
        # "stability": connect_stability_images,
    }


# =============================================================================
# Azure OpenAI (DALL·E 3) call
# =============================================================================

def _call_azure_dalle(
    *,
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    style: str = "vivid",
    response_format: str = "b64_json",
) -> tuple[dict[str, Any] | None, str | None]:
    """Call Azure OpenAI DALL-E 3 Images API. Returns (response_data, error_message)."""
    deployment = (settings.azure_openai_image_deployment or "").strip()
    endpoint = (settings.azure_openai_image_endpoint or settings.azure_openai_endpoint or "").rstrip("/")
    api_key = (settings.azure_openai_subscription_key or "").strip()
    api_version = settings.azure_openai_image_api_version

    if not deployment or not endpoint or not api_key:
        missing: list[str] = []
        if not deployment:
            missing.append("AZURE_OPENAI_IMAGE_DEPLOYMENT")
        if not endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not api_key:
            missing.append("AZURE_OPENAI_SUBSCRIPTION_KEY")
        return None, f"Missing Azure image configuration: {', '.join(missing)}"

    url = f"{endpoint}/openai/deployments/{deployment}/images/generations?api-version={api_version}"
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    body = {
        "prompt": (prompt or "")[:DALLE_PROMPT_MAX_CHARS],
        "size": size,
        "n": 1,
        "quality": quality,
        "style": style,
        "response_format": response_format,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json(), None
    except httpx.HTTPStatusError as e:
        detail = (e.response.text or "").strip()
        msg = f"Azure DALL-E HTTP {e.response.status_code}"
        if detail:
            msg = f"{msg}: {detail[:500]}"
        logger.warning("Azure DALL-E image generation failed: %s", msg)
        return None, msg
    except Exception as e:
        logger.warning("Azure DALL-E image generation failed: %s", e)
        return None, str(e)


def connect_openai_images(*, prompt: str, output_formats: list[str], options: dict[str, Any]) -> dict[str, Any]:
    """
    Connector for Azure OpenAI DALL-E image generation.
    Uses strict per-format controls already set in options by builder.
    """
    size = str(options.get("size") or "1024x1024").strip()
    quality = str(options.get("quality") or "standard").strip().lower()
    style = str(options.get("style") or "vivid").strip().lower()

    api_response, api_error = _call_azure_dalle(
        prompt=prompt,
        size=size if "x" in size else "1024x1024",
        quality=quality if quality in ("standard", "hd") else "standard",
        style=style if style in ("natural", "vivid") else "vivid",
        response_format="b64_json",
    )

    if api_response and "data" in api_response and api_response["data"]:
        item = api_response["data"][0]
        b64 = item.get("b64_json")
        if b64:
            ext = (output_formats[0] if output_formats else "png").lower()
            if ext == "jpg":
                ext = "jpeg"
            file_ext = ext if ext != "jpeg" else "jpg"
            mime = f"image/{ext}"
            image_bytes = base64.b64decode(b64)
            project_id = str(options.get("project_id") or "")
            user_id = str(options.get("user_id") or "")
            topic_title = str(options.get("topic_title") or "")

            saved_path = save_image_bytes_to_local(
                data=image_bytes,
                ext=file_ext,
                project_id=project_id,
                topic_title=topic_title,
            )
            local_filename = saved_path.name if saved_path else f"image_{int(time.time() * 1000)}.{file_ext}"
            orchestrated_artifact_id = str(options.get("artifact_id") or "").strip()
            artifact_key = orchestrated_artifact_id or (saved_path.stem if saved_path else f"img_{int(time.time() * 1000)}")

            blob_ref = upload_artifact_bytes(
                data=image_bytes,
                user_id=user_id or "user",
                project_id=project_id or "project",
                fmt=str(options.get("artifact_format") or "image"),
                artifact_id=artifact_key,
                filename=local_filename,
                content_type=mime,
            )

            uri = blob_ref["uri"] if blob_ref else (str(saved_path) if saved_path else f"data:{mime};base64,{b64}")
            save_error = None if saved_path else "Image generated but local file save failed; returning inline data URI."
            if blob_ref and save_error:
                save_error = "Image uploaded to Azure Blob, but local file save failed."

            return {
                "provider": "openai",
                "status": "generated",
                "prompt": prompt,
                "options": options,
                "error_message": save_error,
                "images": [
                    {
                        "format": file_ext,
                        "mime_type": mime,
                        "uri": uri,
                        "path": str(saved_path) if saved_path else None,
                        "blob_path": (blob_ref or {}).get("blob_path"),
                        "source": "azure_blob" if blob_ref else ("local_disk" if saved_path else "inline_data_uri"),
                    }
                ],
            }
        api_error = "Azure image response missing b64_json in first data item."
    elif api_response:
        api_error = "Azure image response returned no data items."

    # Simulated fallback (kept deterministic-ish for pipeline)
    return {
        "provider": "openai",
        "status": "simulated",
        "prompt": prompt,
        "options": options,
        "error_message": api_error or "Image provider returned no usable image data; simulated response emitted.",
        "images": [
            {
                "format": ext,
                "mime_type": f"image/{'jpeg' if ext == 'jpg' else ext}",
                "uri": f"azure_openai://generated/{ext}/image-1",
            }
            for ext in output_formats
        ],
    }


# =============================================================================
# Format recipes (STRICT)
# =============================================================================

@dataclass(frozen=True)
class FormatRecipe:
    # Provider controls (API knobs)
    size: str
    style: str  # vivid|natural (DALL·E 3 knob)
    # Prompt hint (LLM instruction)
    prompt_hint: str
    # Post-processing defaults (pipeline)
    export_format: str = "png"
    resize_mode: str = "cover"
    sharpen: str = "light"
    denoise: str = "light"


FORMAT_RECIPES: dict[str, FormatRecipe] = {
    "post_image": FormatRecipe(
        size="1024x1024",
        style="vivid",
        prompt_hint=(
            "square social post; subject center-framed or rule-of-thirds with strong visual tension "
            "as a feed thumb-stopper (emotion, contrast, or implied motion); "
            "clean negative space in bottom ~15% for caption safe zone; "
            "no foreground clutter; avoid flat symmetrical layouts"
        ),
        export_format="png",
        resize_mode="cover",
        sharpen="light",
        denoise="light",
    ),
    "thumbnail": FormatRecipe(
        size="1792x1024",
        style="vivid",
        prompt_hint=(
            "thumbnail; one hero subject occupying 60-70% of frame height; "
            "if face present, eyes in upper third of frame; "
            "strong warm-cool contrast between foreground subject and background; "
            "high separation from background; reserve clear negative space right or bottom for headline overlay; "
            "avoid tiny details and busy backgrounds"
        ),
        export_format="jpeg",
        resize_mode="crop",
        sharpen="medium",
        denoise="light",
    ),
    "cover": FormatRecipe(
        size="1024x1792",
        style="natural",
        prompt_hint=(
            "cover; portrait composition; subject centered or upper-centered within 80% safe zone "
            "(10% margin from all edges); subtle tonal darkening or gradient toward lower 20% "
            "for title text overlay; calm premium look; background must not compete near edges"
        ),
        export_format="webp",
        resize_mode="cover",
        sharpen="light",
        denoise="light",
    ),
    "banner": FormatRecipe(
        size="1792x1024",
        style="natural",
        prompt_hint=(
            "banner; horizontal 16:9 wide layout; subject anchored in left third of frame "
            "with shallow depth-of-field; expansive background middle-to-right occupying at least "
            "half the frame width, kept plain for text/logo overlay; panoramic feel — no tight crop"
        ),
        export_format="png",
        resize_mode="contain",
        sharpen="light",
        denoise="light",
    ),
}


# =============================================================================
# Enum label expansions (raw dropdown value → descriptive phrase for prompt)
# Unknown/custom values pass through unchanged.
# =============================================================================

_IMAGE_ENUM_EXPANSIONS: dict[str, dict[str, str]] = {
    "medium": {
        "photo": "photorealistic photography",
        "illustration": "digital illustration",
        "3d_render": "3D CGI render",
        "comic": "comic book art style",
        "watercolor": "watercolor painting",
        "oil_paint": "oil painting with visible brushwork",
        "vector_flat": "flat vector graphic style",
        "pixel_art": "pixel art retro style",
    },
    "texture": {
        "clean": "clean smooth finish, no texture overlay",
        "film_grain": "subtle film grain noise",
        "halftone": "halftone dot pattern",
        "paper": "natural paper texture",
        "canvas": "canvas fabric texture",
        "noise": "digital noise grain",
    },
    "palette_mode": {
        "brand": "brand color palette (see brand colors below)",
        "monochrome": "monochromatic single-tone palette",
        "pastel": "soft pastel tones, low saturation",
        "neon": "vivid neon colors, high saturation",
        "earthy": "earthy organic tones, warm browns and greens",
        "muted": "muted desaturated tones, soft contrast",
        "high_contrast": "high contrast colors, strong separation",
    },
    "lighting": {
        "soft_daylight": "soft natural daylight",
        "golden_hour": "warm golden hour lighting",
        "sunset_warm": "warm sunset glow",
        "overcast_diffused": "overcast diffused ambient light",
        "studio_softbox": "studio softbox lighting",
        "high_key_bright": "high-key bright even lighting",
        "low_key_moody": "low-key moody shadows",
        "neon_night": "neon-lit nighttime atmosphere",
        "backlit_silhouette": "backlit subject creating silhouette effect",
        "rim_light": "rim/edge lighting separating subject from background",
        "volumetric_godrays": "volumetric god rays filtering through atmosphere",
        "dramatic_spotlight": "dramatic hard spotlight",
    },
    "mood": {
        "playful": "playful, light, and fun",
        "serious": "serious and authoritative",
        "premium": "premium, sophisticated, luxury feel",
        "cozy": "warm, cozy, and inviting",
        "dramatic": "dramatic, high-contrast, intense",
        "energetic": "energetic and dynamic",
    },
    "composition": {
        "subject_centered": "subject centered with even surrounding space",
        "rule_of_thirds": "rule-of-thirds framing",
        "negative_space_left": "generous negative space on the left side",
        "negative_space_right": "generous negative space on the right side",
    },
}


def _expand_image_enum(field: str, value: str) -> str:
    """Return the expanded descriptive phrase for a known enum value, or the raw value if unknown."""
    return _IMAGE_ENUM_EXPANSIONS.get(field, {}).get(value, value)


# =============================================================================
# Builder
# =============================================================================

class ImageGenerationBuilder:
    kind = "image"
    formats = {"post_image", "thumbnail", "banner", "cover"}

    # ---- Style settings ingestion (user-provided, model-agnostic) ----

    @staticmethod
    def _image_style_settings(ctx: PipelineContext) -> dict[str, Any]:
        """
        Expected user-facing ImageStyleSettings (model-agnostic), commonly:
          theme, subject_prompt/subject/core_prompt,
          avoid,
          medium/visual_medium, texture,
          palette_mode/color_palette/color_pallete, brand_colors,
          mood,
          composition/focus/focus_negative_space,
          output_fidelity (standard|hd),
          output_formats
        """
        if isinstance(ctx.style_settings, dict) and ctx.style_settings:
            return dict(ctx.style_settings)
        if isinstance(getattr(ctx, "image_style_settings", None), dict):
            return dict(getattr(ctx, "image_style_settings", None))
        return {}

    @staticmethod
    def _normalize_output_formats(raw: Any) -> list[str]:
        allowed = {"png", "jpg", "jpeg", "webp"}
        values = raw if isinstance(raw, list) else ["png"]
        out: list[str] = []
        seen: set[str] = set()
        for item in values:
            ext = str(item).strip().lower()
            if ext == "jpeg":
                ext = "jpg"
            if ext not in allowed or ext in seen:
                continue
            seen.add(ext)
            out.append(ext)
        return out or ["png"]

    # ---- Strict per-format controls (DO NOT ask user) ----

    @staticmethod
    def _recipe_for_format(fmt: str) -> FormatRecipe:
        recipe = FORMAT_RECIPES.get(fmt)
        if not recipe:
            raise ValueError(f"No format recipe configured for '{fmt}'")
        return recipe

    @staticmethod
    def _map_output_fidelity_to_quality(style_settings: dict[str, Any]) -> str:
        """
        DALL·E 3 quality: standard|hd
        User: output_fidelity: standard|hd (case-insensitive)
        """
        fidelity = str(style_settings.get("output_fidelity") or "").strip().lower()
        if fidelity in {"hd", "high", "high_def", "high_definition"}:
            return "hd"
        if fidelity in {"standard", "std"}:
            return "standard"
        return "standard"

    # ---- Prompt builder (precedence-first) ----

    @staticmethod
    def _build_prompt(ctx: PipelineContext, user_style: dict[str, Any], *, fmt: str) -> str:
        """
        Prompt policy:
          - User image settings MUST take precedence (theme/subject/style/composition).
          - Constraints appear early (to survive the 4k cap).
          - Master content appears last as "inspiration only".
        """
        recipe = ImageGenerationBuilder._recipe_for_format(fmt)

        # Helpers (local)
        def _safe(v: Any, *, max_len: int = 800) -> str:
            return str(v or "").strip()[:max_len].strip()

        def _canonicalize_avoid(tag: str) -> str:
            t = re.sub(r"\s+", " ", str(tag or "").strip().lower())
            t = t.replace("-", " ")
            mapping = {
                "watermarks": "watermark",
                "watermark": "watermark",
                "logos": "logo",
                "logo": "logo",
                "ui screenshots": "ui screenshot",
                "ui screenshot": "ui screenshot",
                "gibberish text": "text",
                "illegible text": "text",
                "readable text": "text",
                "typography": "text",
            }
            if t.endswith("s") and t[:-1] in {"watermark", "logo"}:
                t = t[:-1]
            return mapping.get(t, t)

        def _short_master_context(max_len: int = 450) -> str:
            core = _safe(getattr(ctx, "core_idea", "") or "", max_len=180)
            body = _safe(getattr(ctx, "master_body", "") or "", max_len=2000)
            body = re.sub(r"\s+", " ", body)
            snippet = body[:max_len].strip()
            parts: list[str] = []
            if core:
                parts.append(f"Core idea: {core}")
            if snippet:
                parts.append(f"Key cues: {snippet}")
            return " | ".join(parts)[:max_len]

        def _as_bool(value: Any, default: bool = True) -> bool:
            if isinstance(value, bool):
                return value
            if value is None:
                return default
            s = str(value).strip().lower()
            if s in {"1", "true", "yes", "y", "on"}:
                return True
            if s in {"0", "false", "no", "n", "off"}:
                return False
            return default

        # Base metadata (short)
        audience = ctx.target_audience if isinstance(ctx.target_audience, dict) else {}
        segment = _safe(audience.get("primary_segment") or "general audience", max_len=80)
        tone = _safe(getattr(ctx, "tone_preference", None) or "professional", max_len=40)

        fmt_label = fmt.replace("_", " ").strip()
        topic_title = _safe(getattr(ctx, "topic_title", None) or "", max_len=140) or "this topic"

        # User style (primary) + aliases
        theme = _safe(user_style.get("theme"), max_len=240)

        subject_prompt = _safe(
            user_style.get("subject_prompt")
            or user_style.get("subject")
            or user_style.get("core_prompt"),
            max_len=1400,
        )

        medium_raw = _safe(user_style.get("medium") or user_style.get("visual_medium"), max_len=80)
        medium = _expand_image_enum("medium", medium_raw) if medium_raw else ""

        texture_raw = _safe(user_style.get("texture"), max_len=80)
        texture = _expand_image_enum("texture", texture_raw) if texture_raw else ""

        lighting_raw = _safe(user_style.get("lighting"), max_len=80)
        lighting = _expand_image_enum("lighting", lighting_raw) if lighting_raw else ""

        palette_mode_raw = _safe(
            user_style.get("palette_mode")
            or user_style.get("color_palette")
            or user_style.get("color_pallete"),
            max_len=40,
        )
        palette_mode = _expand_image_enum("palette_mode", palette_mode_raw) if palette_mode_raw else ""
        brand_colors = user_style.get("brand_colors") if isinstance(user_style.get("brand_colors"), dict) else {}

        mood_raw = _safe(user_style.get("mood"), max_len=60)
        mood = _expand_image_enum("mood", mood_raw) if mood_raw else ""

        composition_raw = _safe(
            user_style.get("composition")
            or user_style.get("focus")
            or user_style.get("focus_negative_space"),
            max_len=80,
        )
        composition = _expand_image_enum("composition", composition_raw) if composition_raw else ""
        include_master_content = _as_bool(user_style.get("include_master_content"), default=True)

        if not subject_prompt:
            subject_prompt = _safe(
                getattr(ctx, "core_idea", None)
                or getattr(ctx, "topic_title", None)
                or "a clear main subject",
                max_len=300,
            )

        # Avoid (canonicalize + dedupe)
        avoid_list = user_style.get("avoid") if isinstance(user_style.get("avoid"), list) else []
        default_avoid = ["watermarks", "logos", "gibberish text", "illegible text", "distorted hands", "extra fingers"]

        raw_avoid = default_avoid + [str(x).strip() for x in avoid_list if str(x).strip()]
        seen: set[str] = set()
        avoid_dedup: list[str] = []
        for a in raw_avoid:
            key = _canonicalize_avoid(a)
            if not key or key in seen:
                continue
            seen.add(key)
            if key == "watermark":
                avoid_dedup.append("watermarks")
            elif key == "logo":
                avoid_dedup.append("logos")
            elif key == "ui screenshot":
                avoid_dedup.append("ui screenshots")
            elif key == "text":
                avoid_dedup.append("readable text")
            else:
                avoid_dedup.append(a)

        # Compose prompt with precedence
        primary: list[str] = [
            f"FORMAT INTENT: {recipe.prompt_hint}",
            "PRIORITY: Follow the visual brief below strictly. Use reference context only if it does not conflict.",
            f"OUTPUT: single {fmt_label} image for '{topic_title}'. Audience: {segment}. Tone: {tone}.",
        ]
        if theme:
            primary.append(f"Visual motif/theme: {theme}.")
        primary.append(f"SUBJECT (most important): {subject_prompt}")
        if composition:
            primary.append(f"COMPOSITION: {composition}.")

        if fmt == "post_image":
            primary.append(
                "Feed rule: subject must have a strong visual anchor (emotion, contrast, or implied motion) "
                "to stop scroll; avoid flat symmetrical layouts; bottom 15% of frame reserved for caption safe zone."
            )
        elif fmt == "thumbnail":
            primary.append(
                "Thumbnail rule: one hero subject occupying 60-70% of frame height; eyes/face (if present) "
                "in upper third; strong warm-cool contrast between foreground subject and background; "
                "avoid small details and busy backgrounds; clear negative space right or bottom for headline overlay."
            )
        elif fmt == "cover":
            primary.append(
                "Cover rule: keep key subject details within an 80% central safe zone (10% margin from all edges); "
                "subtle tonal darkening or gradient toward the lower 20% for title text overlay; "
                "subject upper-centered or centered; background must not compete near edges."
            )
        elif fmt == "banner":
            primary.append(
                "Banner rule: subject anchored in left third of frame with shallow depth-of-field blur; "
                "right two-thirds kept plain and clean for text/logo overlay; "
                "if conflict, right-side negative space takes priority over all composition preferences; "
                "panoramic expansive feel — no tight crop."
            )

        style_lines: list[str] = []
        if medium:
            style_lines.append(f"Medium: {medium}.")
        if texture:
            style_lines.append(f"Texture: {texture}.")
        if lighting:
            style_lines.append(f"Lighting: {lighting}.")
        if palette_mode:
            style_lines.append(f"Palette mode: {palette_mode}.")
            if palette_mode_raw == "brand" and brand_colors:
                color_parts = [f"{k}={v}" for k, v in brand_colors.items() if str(v).strip()]
                if color_parts:
                    style_lines.append(f"Brand colors: {', '.join(color_parts)}.")
        if mood:
            style_lines.append(f"Mood: {mood}.")

        constraints: list[str] = [
            "Do NOT generate readable text, typography, logos, or watermarks.",
        ]
        if avoid_dedup:
            constraints.append("Avoid / do not include: " + ", ".join(avoid_dedup) + ".")

        reference = _short_master_context(max_len=450) if include_master_content else ""
        reference_block = f"REFERENCE CONTEXT (lowest priority, inspiration only): {reference}" if reference else ""

        blocks = [
            "PRIMARY VISUAL BRIEF:\n" + "\n".join(primary),
            "VISUAL STYLE:\n" + ("\n".join(style_lines) if style_lines else "Use a coherent style consistent with the brief."),
            "CONSTRAINTS:\n" + "\n".join(constraints),
        ]
        if reference_block:
            blocks.append(reference_block)

        return "\n\n".join(blocks)

    # ---- Connector selection ----

    @staticmethod
    def _resolve_connector(style_settings: dict[str, Any]) -> tuple[str, Callable[..., dict[str, Any]]]:
        tool_map = available_image_tools()
        requested_tool = str(style_settings.get("tool_name") or "openai").strip().lower() or "openai"
        tool_name = "openai" if requested_tool in FUTURE_IMAGE_EDIT_TOOL_NAMES else requested_tool
        connector = tool_map.get(tool_name)
        if connector is None:
            valid = ", ".join(sorted(tool_map.keys()))
            raise ValueError(f"Unsupported image tool '{requested_tool}'. Supported tools: {valid}")
        return tool_name, connector

    @staticmethod
    def _extract_source_image_assets(source_payload: dict[str, Any]) -> list[dict[str, Any]]:
        assets = source_payload.get("assets") if isinstance(source_payload.get("assets"), list) else []
        out: list[dict[str, Any]] = []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            mime = str(asset.get("mime_type") or "").strip().lower()
            fmt = str(asset.get("format") or "").strip().lower()
            if mime.startswith("image/") or fmt in {"png", "jpg", "jpeg", "webp"}:
                out.append(asset)
        return out

    @staticmethod
    def _resolve_source_blob_paths(
        source_blob_paths: list[str] | None,
        source_image_assets: list[dict[str, Any]],
    ) -> list[str]:
        preferred = [str(p or "").strip() for p in (source_blob_paths or []) if str(p or "").strip()]
        if preferred:
            return preferred
        from_assets: list[str] = []
        seen: set[str] = set()
        for asset in source_image_assets:
            blob_path = str(asset.get("blob_path") or "").strip()
            if not blob_path:
                uri = str(asset.get("uri") or "").strip()
                blob_path = str(blob_path_from_uri(uri) or "").strip()
            if blob_path and blob_path not in seen:
                seen.add(blob_path)
                from_assets.append(blob_path)
        return from_assets

    @staticmethod
    def _load_source_image_bytes(blob_paths: list[str]) -> tuple[bytes | None, str | None]:
        for blob_path in blob_paths:
            data = download_bytes(blob_path=blob_path)
            if data:
                return data, blob_path
        return None, None

    # ---- Normalized settings snapshot ----

    @staticmethod
    def _normalized_image_style_snapshot(user_style: dict[str, Any]) -> dict[str, Any]:
        """
        Persist a compact snapshot of *effective* user inputs (including aliases).
        This improves reproducibility/debugging and prevents losing fields when UI evolves.
        """
        snap: dict[str, Any] = {
            "theme": user_style.get("theme"),
            "subject_prompt": user_style.get("subject_prompt") or user_style.get("subject") or user_style.get("core_prompt"),
            "avoid": user_style.get("avoid"),
            "medium": user_style.get("medium") or user_style.get("visual_medium"),
            "texture": user_style.get("texture"),
            "palette_mode": user_style.get("palette_mode") or user_style.get("color_palette") or user_style.get("color_pallete"),
            "brand_colors": user_style.get("brand_colors"),
            "mood": user_style.get("mood"),
            "composition": user_style.get("composition") or user_style.get("focus") or user_style.get("focus_negative_space"),
            "output_fidelity": user_style.get("output_fidelity"),
            "include_master_content": user_style.get("include_master_content"),
        }
        # drop empties
        return {k: v for k, v in snap.items() if v not in (None, "", [], {})}

    # ---- Public API ----

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        if fmt not in self.formats:
            raise ValueError(f"Unsupported image format for image builder: {fmt}")

        recipe = self._recipe_for_format(fmt)

        # User style settings
        user_style = self._image_style_settings(ctx)

        # Strict per-format controls (user cannot override)
        strict_controls: dict[str, Any] = {
            "artifact_format": fmt,
            "tool_name": "openai",
            "size": recipe.size,
            "style": recipe.style,  # vivid/natural
            "quality": self._map_output_fidelity_to_quality(user_style),  # standard/hd
            # pipeline defaults
            "export_format": recipe.export_format,
            "resize_mode": recipe.resize_mode,
            "sharpen": recipe.sharpen,
            "denoise": recipe.denoise,
        }

        # Output formats (user-configurable) defaulting to recipe.export_format
        output_formats = self._normalize_output_formats(user_style.get("output_formats") or [recipe.export_format])

        # Build prompt
        prompt = self._build_prompt(ctx, user_style, fmt=fmt)

        # Options passed to connector
        options = dict(user_style)
        options.update(strict_controls)

        # Required metadata for storage
        options.setdefault("project_id", getattr(ctx, "project_id", "") or "")
        options.setdefault("user_id", getattr(ctx, "user_id", "") or "")
        options.setdefault("topic_title", getattr(ctx, "topic_title", "") or "")

        tool_name, connector = self._resolve_connector(options)
        tool_response = connector(prompt=prompt, output_formats=output_formats, options=options)

        # Payload
        payload = default_payload_template()
        payload["body"] = None
        payload["assets"] = tool_response.get("images", [])
        payload["prompts"] = [
            {"name": "image_prompt", "text": prompt, "tool": tool_response.get("provider", tool_name)}
        ]
        payload["settings"] = {
            "artifact_format": fmt,
            "tool_name": tool_name,
            "output_formats": output_formats,
            # strict generation controls
            "size": recipe.size,
            "style": recipe.style,
            "quality": strict_controls["quality"],
            # pipeline defaults
            "export_format": recipe.export_format,
            "resize_mode": recipe.resize_mode,
            "sharpen": recipe.sharpen,
            "denoise": recipe.denoise,
            "status": tool_response.get("status", "simulated"),
        }

        # Persist normalized user style snapshot
        image_style_snapshot = self._normalized_image_style_snapshot(user_style)
        if image_style_snapshot:
            payload["settings"]["image_style"] = image_style_snapshot

        if tool_response.get("error_message"):
            payload["settings"]["error_message"] = str(tool_response.get("error_message"))

        payload["notes"] = "Image generation produced via selected connector with strict per-format controls."

        tags = [x for x in (ctx.seed_keywords or []) if isinstance(x, str) and x.strip()]
        custom_title = ""
        if isinstance(getattr(ctx, "style_settings", None), dict):
            custom_title = str(ctx.style_settings.get("default_artifact_title") or "").strip()
        if custom_title and len(getattr(ctx, "requested_formats", []) or []) > 1:
            title = f"{custom_title} - {fmt.replace('_', ' ').title()}"
        else:
            title = custom_title or f"{getattr(ctx, 'topic_title', '')} - {fmt.replace('_', ' ').title()}".strip(" -")
        draft_status = str(tool_response.get("status") or "generated").strip().lower() or "generated"
        return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status=draft_status)

    def edit(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        source_artifact: dict[str, Any],
        edit_instruction: str,
        target_artifact_id: str | None = None,
        source_blob_paths: list[str] | None = None,
    ) -> ArtifactDraft:
        if fmt not in self.formats:
            raise ValueError(f"Unsupported image format for image builder edit: {fmt}")

        source_payload = source_artifact.get("payload_json") if isinstance(source_artifact, dict) else {}
        source_payload = source_payload if isinstance(source_payload, dict) else {}
        source_settings = source_payload.get("settings") if isinstance(source_payload.get("settings"), dict) else {}
        source_prompts = source_payload.get("prompts") if isinstance(source_payload.get("prompts"), list) else []
        source_image_assets = self._extract_source_image_assets(source_payload)
        resolved_source_blob_paths = self._resolve_source_blob_paths(source_blob_paths, source_image_assets)
        source_image_bytes, source_image_blob_path = self._load_source_image_bytes(resolved_source_blob_paths)
        source_image_asset = source_image_assets[0] if source_image_assets else {}

        original_prompt = ""
        for item in source_prompts:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text:
                original_prompt = text
                break

        cleaned_instruction = str(edit_instruction or "").strip()
        if not cleaned_instruction:
            raise ValueError("edit_instruction is required")

        if not original_prompt:
            style_from_ctx = self._image_style_settings(ctx)
            original_prompt = self._build_prompt(ctx, style_from_ctx, fmt=fmt)

        revised_prompt = (
            "ITERATION REQUEST (apply these changes while preserving the original concept):\n"
            f"{cleaned_instruction}\n\n"
            "ORIGINAL CREATIVE BRIEF:\n"
            f"{original_prompt}\n"
        ).strip()

        recipe = self._recipe_for_format(fmt)
        user_style = source_settings.get("image_style") if isinstance(source_settings.get("image_style"), dict) else {}
        if not user_style:
            user_style = self._image_style_settings(ctx)

        strict_controls: dict[str, Any] = {
            "artifact_format": fmt,
            "tool_name": str(source_settings.get("tool_name") or "openai").strip().lower() or "openai",
            "requested_tool_name": str(source_settings.get("tool_name") or "openai").strip().lower() or "openai",
            "size": str(source_settings.get("size") or recipe.size).strip(),
            "style": str(source_settings.get("style") or recipe.style).strip().lower(),
            "quality": str(source_settings.get("quality") or self._map_output_fidelity_to_quality(user_style)).strip().lower(),
            "export_format": str(source_settings.get("export_format") or recipe.export_format).strip().lower(),
            "resize_mode": str(source_settings.get("resize_mode") or recipe.resize_mode).strip().lower(),
            "sharpen": str(source_settings.get("sharpen") or recipe.sharpen).strip().lower(),
            "denoise": str(source_settings.get("denoise") or recipe.denoise).strip().lower(),
        }
        output_formats = self._normalize_output_formats(source_settings.get("output_formats") or [strict_controls["export_format"]])

        options = dict(user_style)
        options.update(strict_controls)
        options.setdefault("project_id", getattr(ctx, "project_id", "") or "")
        options.setdefault("user_id", getattr(ctx, "user_id", "") or "")
        options.setdefault("topic_title", getattr(ctx, "topic_title", "") or "")
        # Forward-compatible payload for future edits/img2img connectors.
        options["source_artifact"] = source_artifact
        options["source_blob_paths"] = list(resolved_source_blob_paths)
        options["source_image_blob_path"] = source_image_blob_path
        options["source_image_mime_type"] = str(source_image_asset.get("mime_type") or "").strip() or "image/png"
        options["source_image_uri"] = str(source_image_asset.get("uri") or "").strip() or None
        options["source_image_bytes"] = source_image_bytes
        if str(target_artifact_id or "").strip():
            options["artifact_id"] = str(target_artifact_id).strip()

        tool_name, connector = self._resolve_connector(options)
        tool_response = connector(prompt=revised_prompt, output_formats=output_formats, options=options)

        payload = default_payload_template()
        payload["body"] = None
        payload["assets"] = tool_response.get("images", [])
        payload["prompts"] = [
            {"name": "original_prompt", "text": original_prompt, "tool": "source_artifact"},
            {"name": "iterate_instruction", "text": cleaned_instruction, "tool": "user"},
            {"name": "image_prompt", "text": revised_prompt, "tool": tool_response.get("provider", tool_name)},
        ]
        payload["settings"] = {
            "artifact_format": fmt,
            "tool_name": tool_name,
            "requested_tool_name": strict_controls["requested_tool_name"],
            "output_formats": output_formats,
            "size": strict_controls["size"],
            "style": strict_controls["style"],
            "quality": strict_controls["quality"],
            "export_format": strict_controls["export_format"],
            "resize_mode": strict_controls["resize_mode"],
            "sharpen": strict_controls["sharpen"],
            "denoise": strict_controls["denoise"],
            "status": tool_response.get("status", "simulated"),
            "generation_source": "iterate_edit",
            "iterate_strategy": "prompt_regeneration",
            "edit_instruction": cleaned_instruction,
            "source_blob_paths": list(resolved_source_blob_paths),
            "source_image_blob_path_used": source_image_blob_path,
            "source_image_bytes_available": bool(source_image_bytes),
        }

        image_style_snapshot = self._normalized_image_style_snapshot(user_style)
        if image_style_snapshot:
            payload["settings"]["image_style"] = image_style_snapshot
        if tool_response.get("error_message"):
            payload["settings"]["error_message"] = str(tool_response.get("error_message"))
        payload["notes"] = "Image iteration generated from original prompt + iterate instruction."

        tags = source_artifact.get("tags_json") if isinstance(source_artifact, dict) and isinstance(source_artifact.get("tags_json"), list) else []
        if not tags:
            tags = [x for x in (ctx.seed_keywords or []) if isinstance(x, str) and x.strip()]
        title = str(source_artifact.get("title") or "").strip() if isinstance(source_artifact, dict) else ""
        if not title:
            title = f"{getattr(ctx, 'topic_title', '')} - {fmt.replace('_', ' ').title()}".strip(" -")
        draft_status = str(tool_response.get("status") or "generated").strip().lower() or "generated"
        return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status=draft_status)


BUILDER = ImageGenerationBuilder()
