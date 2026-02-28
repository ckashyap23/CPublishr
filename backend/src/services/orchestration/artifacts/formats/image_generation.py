from __future__ import annotations

import base64
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx

from src.core.config import settings
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext
from src.services.storage.artifact_blob_storage import upload_bytes

logger = logging.getLogger(__name__)

IMAGES_DIR = Path(__file__).resolve().parent / "images"

DALLE_PROMPT_MAX_CHARS = 4000


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


def _save_image_to_disk(b64_data: str, ext: str, project_id: str = "", topic_title: str = "") -> Path | None:
    """Save base64 image to backend/.../artifacts/formats/images/. Returns path or None."""
    try:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^\w\-]", "_", (topic_title or project_id or "image")[:60]).strip("_") or "image"
        filename = f"{slug}_{int(time.time() * 1000)}.{ext}"
        path = IMAGES_DIR / filename
        path.write_bytes(base64.b64decode(b64_data))
        return path
    except Exception as e:
        logger.warning("Failed to save image to disk: %s", e)
        return None


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

            saved_path = _save_image_to_disk(b64, file_ext, project_id, topic_title)
            local_filename = saved_path.name if saved_path else f"image_{int(time.time() * 1000)}.{file_ext}"
            artifact_key = saved_path.stem if saved_path else f"img_{int(time.time() * 1000)}"

            blob_ref = upload_bytes(
                data=image_bytes,
                user_id=user_id or "user",
                project_id=project_id or "project",
                format=str(options.get("artifact_format") or "image"),
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
            "square social post; balanced composition with clean negative space for optional caption; "
            "subject clear and uncluttered"
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
            "thumbnail; strong subject clarity, close framing, high separation from background; "
            "reserve clear negative space for headline overlay; avoid tiny details/busy backgrounds"
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
            "cover; portrait composition with calm premium framing; preserve safe areas; "
            "background minimal, avoid clutter near edges"
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
            "banner; wide layout emphasizing clean negative space (preferably right) for optional text/logo; "
            "background plain and simple"
        ),
        export_format="png",
        resize_mode="contain",
        sharpen="light",
        denoise="light",
    ),
}


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

        medium = _safe(user_style.get("medium") or user_style.get("visual_medium"), max_len=80)
        texture = _safe(user_style.get("texture"), max_len=80)

        palette_mode = _safe(
            user_style.get("palette_mode")
            or user_style.get("color_palette")
            or user_style.get("color_pallete"),
            max_len=40,
        )
        brand_colors = user_style.get("brand_colors") if isinstance(user_style.get("brand_colors"), dict) else {}

        mood = _safe(user_style.get("mood"), max_len=60)
        composition = _safe(
            user_style.get("composition")
            or user_style.get("focus")
            or user_style.get("focus_negative_space"),
            max_len=80,
        )
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

        if fmt == "thumbnail":
            primary.append("Thumbnail rule: one hero subject, large and readable; strong separation from background; avoid small details.")
        elif fmt == "cover":
            primary.append("Cover rule: keep key subject details within a central safe area (leave ~10% margin from edges).")
        elif fmt == "banner":
            primary.append("Banner rule: reserve clean negative space on the right for optional text/logo; if conflict, prioritize this over other composition preferences.")

        style_lines: list[str] = []
        if medium:
            style_lines.append(f"Medium: {medium}.")
        if texture:
            style_lines.append(f"Texture: {texture}.")
        if palette_mode:
            style_lines.append(f"Palette mode: {palette_mode}.")
            if palette_mode == "brand" and brand_colors:
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
        tool_name = str(style_settings.get("tool_name") or "openai").strip().lower() or "openai"
        connector = tool_map.get(tool_name)
        if connector is None:
            valid = ", ".join(sorted(tool_map.keys()))
            raise ValueError(f"Unsupported image tool '{tool_name}'. Supported tools: {valid}")
        return tool_name, connector

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
        title = f"{getattr(ctx, 'topic_title', '')} - {fmt.replace('_', ' ').title()}".strip(" -")
        draft_status = str(tool_response.get("status") or "generated").strip().lower() or "generated"
        return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status=draft_status)


BUILDER = ImageGenerationBuilder()
