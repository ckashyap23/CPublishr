from __future__ import annotations

import base64
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable

import httpx

IMAGES_DIR = Path(__file__).resolve().parent / "images"

from src.core.config import settings
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext
from src.services.storage.artifact_blob_storage import upload_bytes

logger = logging.getLogger(__name__)


def available_image_tools() -> dict[str, Callable[..., dict[str, Any]]]:
    """Return supported third-party image tool connectors."""
    return {
        "openai": connect_openai_images,
        #"stability": connect_stability_images,
    }


def image_tool_aliases() -> dict[str, str]:
    """Normalize common provider aliases to a canonical tool key."""
    return {
        "azure_openai": "openai",
        "gpt-image-1": "openai",
        "stabilityai": "stability",
    }


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
    endpoint = (settings.azure_openai_endpoint or "").rstrip("/")
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
    """Connector for Azure OpenAI DALL-E image generation. Falls back to simulated if not configured."""
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
                format="image_generation",
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


class ImageGenerationBuilder:
    kind = "image"
    formats = {"image_generation"}

    @staticmethod
    def _normalize_output_formats(raw: Any) -> list[str]:
        allowed = {"png", "jpg", "jpeg", "webp"}
        values = raw if isinstance(raw, list) else ["png", "jpg"]
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
        return out or ["png", "jpg"]

    @staticmethod
    def _build_prompt(ctx: PipelineContext) -> str:
        audience = ctx.target_audience if isinstance(ctx.target_audience, dict) else {}
        segment = str(audience.get("primary_segment") or "general audience").strip()
        tone = str(ctx.tone_preference or "professional").strip()
        return (
            f"Create a high-quality image for '{ctx.topic_title}'. "
            f"Core idea: {ctx.core_idea or 'not specified'}. "
            f"Audience: {segment}. Tone: {tone}. "
            f"Reference context: {(ctx.master_body or 'not specified')[:1200]}"
        )

    @staticmethod
    def _resolve_connector(style_settings: dict[str, Any]) -> tuple[str, Callable[..., dict[str, Any]]]:
        tool_map = available_image_tools()
        aliases = image_tool_aliases()

        explicit_connector = style_settings.get("tool_connector")
        if callable(explicit_connector):
            explicit_name = str(style_settings.get("tool_name") or "custom").strip().lower() or "custom"
            return explicit_name, explicit_connector

        raw_tool_name = str(
            style_settings.get("tool_name")
            or style_settings.get("connector_name")
            or style_settings.get("tool")
            or ""
        ).strip().lower()

        normalized_name = aliases.get(raw_tool_name, raw_tool_name)
        if not normalized_name:
            raise ValueError("Missing image tool selection. Provide style_settings.tool_name.")
        connector = tool_map.get(normalized_name)
        if connector is None:
            valid = ", ".join(sorted(tool_map.keys()))
            raise ValueError(f"Unsupported image tool '{raw_tool_name}'. Supported tools: {valid}")
        return normalized_name, connector

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        if fmt not in self.formats:
            raise ValueError(f"Unsupported image format for image builder: {fmt}")

        style_settings = ctx.style_settings if isinstance(ctx.style_settings, dict) else {}
        output_formats = self._normalize_output_formats(style_settings.get("output_formats"))
        tool_name, connector = self._resolve_connector(style_settings)

        prompt = self._build_prompt(ctx)
        options = dict(style_settings)
        options.setdefault("project_id", ctx.project_id)
        options.setdefault("user_id", ctx.user_id)
        options.setdefault("topic_title", ctx.topic_title)
        tool_response = connector(prompt=prompt, output_formats=output_formats, options=options)

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
            "tool_name": tool_name,
            "output_formats": output_formats,
            "status": tool_response.get("status", "simulated"),
        }
        if tool_response.get("error_message"):
            payload["settings"]["error_message"] = str(tool_response.get("error_message"))
        payload["notes"] = "Image generation produced via selected third-party connector."

        tags = [x for x in ctx.seed_keywords if isinstance(x, str) and x.strip()]
        title = f"{ctx.topic_title} - Image Generation"
        return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags)


BUILDER = ImageGenerationBuilder()
