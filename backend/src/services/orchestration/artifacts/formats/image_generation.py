from __future__ import annotations

import base64
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx

IMAGES_DIR = Path(__file__).resolve().parent / "images"

from src.core.config import settings
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext
from src.services.storage.artifact_blob_storage import upload_bytes

logger = logging.getLogger(__name__)


# ----------------------------
# Provider connector registry
# ----------------------------

def available_image_tools() -> dict[str, Callable[..., dict[str, Any]]]:
    """Return supported third-party image tool connectors."""
    return {
        "openai": connect_openai_images,
        # "stability": connect_stability_images,
    }


# ----------------------------
# Azure OpenAI (DALL·E 3) call
# ----------------------------

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
        "prompt": prompt[:4000],
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

    # Simulated fallback
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
                "uri": f"openai://generated/{ext}/image-1",
            }
            for ext in output_formats
        ],
    }


# ----------------------------
# Format recipes (STRICT)
# ----------------------------

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
    # Square social post
    "post_image": FormatRecipe(
        size="1024x1024",
        style="vivid",
        prompt_hint=(
            "Format intent: square social post. Balanced composition with clean negative space for optional caption. "
            "Keep the subject clear and uncluttered."
        ),
        export_format="png",
        resize_mode="cover",
        sharpen="light",
        denoise="light",
    ),
    # Wide, punchy thumbnail
    "thumbnail": FormatRecipe(
        size="1792x1024",
        style="vivid",
        prompt_hint=(
            "Format intent: thumbnail. Strong subject clarity, close framing, high separation from background. "
            "Reserve clear negative space for a headline overlay; avoid tiny details and busy backgrounds."
        ),
        export_format="jpeg",
        resize_mode="crop",
        sharpen="medium",
        denoise="light",
    ),
    # Tall cover (your earlier defaults used portrait for cover)
    "cover": FormatRecipe(
        size="1024x1792",
        style="natural",
        prompt_hint=(
            "Format intent: cover. Portrait composition with calm, premium framing. "
            "Preserve safe areas; keep background minimal and avoid clutter near edges."
        ),
        export_format="webp",
        resize_mode="cover",
        sharpen="light",
        denoise="light",
    ),
    # Wide banner
    "banner": FormatRecipe(
        size="1792x1024",
        style="natural",
        prompt_hint=(
            "Format intent: banner. Wide layout emphasizing clean negative space (preferably on the right) "
            "for optional text/logo. Keep background plain to simple."
        ),
        export_format="png",
        resize_mode="contain",
        sharpen="light",
        denoise="light",
    ),
}


# ----------------------------
# Builder
# ----------------------------

class ImageGenerationBuilder:
    kind = "image"
    formats = {"post_image", "thumbnail", "banner", "cover"}

    # ---- Style settings ingestion (user-provided, model-agnostic) ----

    @staticmethod
    def _image_style_settings(ctx: PipelineContext) -> dict[str, Any]:
        """
        Expected user-facing CommonStyleSettings (model-agnostic), e.g.:
          theme, subject_prompt, avoid,
          medium, texture,
          palette_mode, brand_colors,
          mood, focus_negative_space,
          output_fidelity (standard|hd)
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
        User: output_fidelity: Standard|HD (case-insensitive)
        """
        fidelity = str(style_settings.get("output_fidelity") or "").strip().lower()
        if fidelity in {"hd", "high", "high_def", "high_definition"}:
            return "hd"
        if fidelity in {"standard", "std"}:
            return "standard"
        # default
        return "standard"

    # ---- Prompt builder (includes common style + strict format hint) ----

    @staticmethod
    def _build_prompt(ctx: PipelineContext, user_style: dict[str, Any], *, fmt: str) -> str:
        recipe = ImageGenerationBuilder._recipe_for_format(fmt)

        # Base context (content)
        audience = ctx.target_audience if isinstance(ctx.target_audience, dict) else {}
        segment = str(audience.get("primary_segment") or "general audience").strip()
        tone = str(ctx.tone_preference or "professional").strip()

        base_context = (
            f"Create a high-quality {fmt.replace('_', ' ')} image for '{ctx.topic_title}'. "
            f"Core idea: {ctx.core_idea or 'not specified'}. "
            f"Audience: {segment}. Tone: {tone}. "
            f"Reference context (for grounding only): {(ctx.master_body or 'not specified')[:1200]}"
        )

        # User style (model-agnostic)
        theme = str(user_style.get("theme") or "").strip()
        subject_prompt = str(user_style.get("subject_prompt") or "").strip()

        # Negative intent list
        avoid_list = user_style.get("avoid") if isinstance(user_style.get("avoid"), list) else []

        medium = str(user_style.get("medium") or "").strip()
        texture = str(user_style.get("texture") or "").strip()

        palette_mode = str(user_style.get("palette_mode") or "").strip()
        brand_colors = user_style.get("brand_colors") if isinstance(user_style.get("brand_colors"), dict) else {}

        mood = str(user_style.get("mood") or "").strip()
        focus = str(user_style.get("focus_negative_space") or "").strip()

        # Compose prompt blocks
        style_lines: list[str] = []
        style_lines.append(recipe.prompt_hint)

        # High signal creative direction
        if theme:
            style_lines.append(f"Theme: {theme}.")
        if subject_prompt:
            style_lines.append(f"Subject description: {subject_prompt}")

        # Visual style
        if medium:
            style_lines.append(f"Visual medium: {medium}.")
        if texture:
            style_lines.append(f"Texture: {texture}.")

        # Color
        if palette_mode:
            style_lines.append(f"Color palette mode: {palette_mode}.")
            if palette_mode == "brand" and brand_colors:
                color_parts = [f"{k}={v}" for k, v in brand_colors.items() if str(v).strip()]
                if color_parts:
                    style_lines.append(f"Use brand colors: {', '.join(color_parts)}.")

        # Mood
        if mood:
            style_lines.append(f"Mood: {mood}.")

        # Composition
        if focus:
            style_lines.append(f"Composition focus: {focus}.")

        # Negatives (always include some common ones even if user didn't provide)
        default_avoid = [
            "watermarks",
            "gibberish text",
            "illegible text",
            "distorted hands",
            "extra fingers",
        ]
        avoid_items = []
        avoid_items.extend([x for x in default_avoid if isinstance(x, str) and x.strip()])
        avoid_items.extend([str(x).strip() for x in avoid_list if str(x).strip()])

        # De-dup
        seen = set()
        avoid_items_dedup = []
        for a in avoid_items:
            key = a.lower()
            if key in seen:
                continue
            seen.add(key)
            avoid_items_dedup.append(a)

        if avoid_items_dedup:
            style_lines.append(f"Avoid / do not include: {', '.join(avoid_items_dedup)}.")

        # Guardrails: request no text rendering (you’ll overlay text later)
        style_lines.append("Do not generate any readable text or typography in the image.")

        return f"{base_context}\n\nCreative direction and constraints:\n" + "\n".join(style_lines)

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

    # ---- Public API ----

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        if fmt not in self.formats:
            raise ValueError(f"Unsupported image format for image builder: {fmt}")

        recipe = self._recipe_for_format(fmt)

        # User-provided common style settings
        user_style = self._image_style_settings(ctx)

        # Strict per-format controls (do NOT let user override these via style settings)
        strict_controls: dict[str, Any] = {
            "artifact_format": fmt,
            "tool_name": "openai",
            "size": recipe.size,
            "style": recipe.style,  # vivid/natural (DALL·E 3)
            "quality": self._map_output_fidelity_to_quality(user_style),  # standard/hd
            # pipeline defaults:
            "export_format": recipe.export_format,
            "resize_mode": recipe.resize_mode,
            "sharpen": recipe.sharpen,
            "denoise": recipe.denoise,
        }

        # Output formats can be user-configurable (e.g., png/webp) but default from recipe.export_format
        output_formats = self._normalize_output_formats(user_style.get("output_formats") or [recipe.export_format])

        # Build final prompt (includes format prompt hint + user style)
        prompt = self._build_prompt(ctx, user_style, fmt=fmt)

        # Options passed to connector: merge user_style + strict_controls with strict taking precedence
        options = dict(user_style)
        options.update(strict_controls)

        # Required metadata for storage
        options.setdefault("project_id", ctx.project_id)
        options.setdefault("user_id", ctx.user_id)
        options.setdefault("topic_title", ctx.topic_title)

        tool_name, connector = self._resolve_connector(options)
        tool_response = connector(prompt=prompt, output_formats=output_formats, options=options)

        # Build payload
        payload = default_payload_template()
        payload["body"] = None
        payload["assets"] = tool_response.get("images", [])
        payload["prompts"] = [
            {
                "name": "image_prompt",
                "text": prompt,
                "tool": tool_response.get("provider", tool_name),
            }
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

        # Store a compact snapshot of user-facing style settings for reproducibility/debugging
        image_style_for_settings: dict[str, Any] = {}
        for key in (
            "theme",
            "subject_prompt",
            "avoid",
            "medium",
            "texture",
            "palette_mode",
            "brand_colors",
            "mood",
            "focus_negative_space",
            "output_fidelity",
        ):
            if key in user_style:
                image_style_for_settings[key] = user_style.get(key)

        if image_style_for_settings:
            payload["settings"]["image_style"] = image_style_for_settings

        if tool_response.get("error_message"):
            payload["settings"]["error_message"] = str(tool_response.get("error_message"))

        payload["notes"] = "Image generation produced via selected third-party connector with strict per-format controls."

        tags = [x for x in ctx.seed_keywords if isinstance(x, str) and x.strip()]
        title = f"{ctx.topic_title} - {fmt.replace('_', ' ').title()}"
        draft_status = str(tool_response.get("status") or "generated").strip().lower() or "generated"
        return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status=draft_status)


BUILDER = ImageGenerationBuilder()
