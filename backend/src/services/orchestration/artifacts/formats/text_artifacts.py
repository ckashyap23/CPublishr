from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext

TEXT_DIR = Path(__file__).resolve().parent / "text"
logger = logging.getLogger(__name__)


TEXT_FORMATS = {
    "caption",
    "x_post",  # post
    "newsletter",
    "blog_long",  # blog
    "script_short",  # script
    "cta_variants",  # cta
}


def _save_text_to_disk(
    text_data: str,
    *,
    ext: str = "txt",
    project_id: str = "",
    topic_title: str = "",
    fmt: str = "",
) -> Path | None:
    """Save text output to backend/.../artifacts/formats/text/. Returns path or None."""
    try:
        TEXT_DIR.mkdir(parents=True, exist_ok=True)
        seed = f"{topic_title or project_id or 'text'}_{fmt or 'artifact'}"
        slug = re.sub(r"[^\w\-]", "_", seed[:80]).strip("_") or "text_artifact"
        file_ext = (ext or "txt").strip().lower()
        filename = f"{slug}_{int(time.time() * 1000)}.{file_ext}"
        path = TEXT_DIR / filename
        path.write_text(text_data or "", encoding="utf-8")
        return path
    except Exception as e:
        logger.warning("Failed to save text artifact to disk: %s", e)
        return None


class TextArtifactsBuilder:
    kind = "text"
    formats = set(TEXT_FORMATS)

    def __init__(self, llm: AzureOpenAIClient | None = None):
        self.llm = llm or AzureOpenAIClient()
        self.enable_llm = bool(settings.artifact_text_llm_enabled)

    @staticmethod
    def _audience_values(ctx: PipelineContext) -> tuple[str, str]:
        audience = ctx.target_audience if isinstance(ctx.target_audience, dict) else {}
        segment = str(audience.get("primary_segment") or "general").strip()
        notes = str(audience.get("notes") or "").strip() or "not specified"
        return segment, notes

    @staticmethod
    def _base_settings(ctx: PipelineContext) -> dict[str, Any]:
        segment, notes = TextArtifactsBuilder._audience_values(ctx)
        settings_out = {
            "language": "en",
            "tone": ctx.tone_preference or "professional",
            "audience_familiarity": ctx.audience_familiarity or "somewhat_familiar",
            "detail_level": ctx.detail_level or "practical",
            "target_audience": segment,
            "target_audience_notes": notes,
        }
        if isinstance(ctx.style_settings, dict):
            settings_out.update(ctx.style_settings)
        return settings_out

    @staticmethod
    def _format_rule(fmt: str) -> str:
        if fmt in {"caption", "x_post", "blog_long", "newsletter"}:
            return "Use payload.body (string). payload.items must be []."
        if fmt == "script_short":
            return 'Use payload.items beat objects: [{"item_type":"beat","sequence":1,"text":"..."}], body=null.'
        if fmt == "cta_variants":
            return 'Use payload.items cta objects: [{"item_type":"cta","sequence":1,"text":"..."}], body=null.'
        return "Use valid envelope fields only."

    def _fallback_payload(self, *, fmt: str, ctx: PipelineContext) -> dict[str, Any]:
        payload = default_payload_template()
        payload["settings"] = self._base_settings(ctx)
        excerpt = (ctx.master_body or "not specified").strip()
        if fmt in {"caption", "x_post", "blog_long", "newsletter"}:
            payload["body"] = excerpt[:1800] or "not specified"
            payload["items"] = []
        elif fmt == "script_short":
            payload["body"] = None
            payload["items"] = [
                {"item_type": "beat", "sequence": 1, "text": "not specified"},
                {"item_type": "beat", "sequence": 2, "text": "not specified"},
            ]
            payload["settings"]["target_duration_sec"] = 30
        elif fmt == "cta_variants":
            payload["body"] = None
            payload["items"] = [
                {"item_type": "cta", "sequence": 1, "text": "not specified"},
                {"item_type": "cta", "sequence": 2, "text": "not specified"},
            ]
        return payload

    def _generate_with_llm(self, *, fmt: str, ctx: PipelineContext) -> dict[str, Any]:
        if not (self.enable_llm and self.llm and self.llm.enabled):
            return {}
        audience_segment, audience_notes = self._audience_values(ctx)
        system_prompt = """
You generate ONE text artifact as strict JSON.
Output only JSON object with keys: title, payload_json, tags_json.
No markdown fences. No extra keys. No new facts.
""".strip()
        user_prompt = f"""
Create one artifact for format={fmt}.
topic_title={ctx.topic_title}
core_idea={ctx.core_idea}
master_body={ctx.master_body[:6000]}
seed_keywords={json.dumps(ctx.seed_keywords, ensure_ascii=False)}
target_audience={audience_segment}
target_audience_notes={audience_notes}
audience_familiarity={ctx.audience_familiarity or "not specified"}
detail_level={ctx.detail_level or "not specified"}
tone_preference={ctx.tone_preference or "not specified"}
style_settings={json.dumps(ctx.style_settings or {}, ensure_ascii=False)}

Shape rule:
{self._format_rule(fmt)}

Envelope:
{{
  "version": "1.0",
  "body": null,
  "items": [],
  "assets": [],
  "prompts": [],
  "settings": {{}},
  "notes": null
}}
""".strip()
        raw = self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2, max_tokens=1800)
        parsed = parse_json_object(raw) or {}
        if not parsed:
            logger.warning(
                "TextArtifactsBuilder LLM returned unparseable JSON: fmt=%s chars=%s preview=%r",
                fmt,
                len(raw or ""),
                (raw or "")[:240],
            )
        return parsed

    def _merge_payload(self, *, payload: dict[str, Any] | None, fmt: str, ctx: PipelineContext) -> dict[str, Any]:
        merged = default_payload_template()
        if isinstance(payload, dict):
            merged.update(payload)
        if not isinstance(merged.get("settings"), dict):
            merged["settings"] = {}
        for k, v in self._base_settings(ctx).items():
            merged["settings"].setdefault(k, v)
        if fmt in {"caption", "x_post", "blog_long", "newsletter"}:
            if not isinstance(merged.get("body"), str) or not str(merged.get("body")).strip():
                merged["body"] = "not specified"
            merged["items"] = []
        else:
            merged["body"] = None
            if not isinstance(merged.get("items"), list):
                merged["items"] = []
        merged.pop("keywords", None)
        merged.pop("tags_json", None)
        return merged

    @staticmethod
    def _normalize_tags(values: Any, fallback: list[str]) -> list[str]:
        src = values if isinstance(values, list) else fallback
        out: list[str] = []
        seen: set[str] = set()
        for x in src:
            s = str(x).strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        return out

    @staticmethod
    def _text_output_for_disk(*, fmt: str, payload: dict[str, Any]) -> tuple[str, str]:
        if fmt in {"caption", "x_post", "blog_long", "newsletter"}:
            body = payload.get("body")
            return (str(body) if body is not None else "", "txt")
        return (json.dumps(payload, ensure_ascii=False, indent=2), "json")

    @staticmethod
    def _local_text_asset(*, path: Path, ext: str, fmt: str) -> dict[str, Any]:
        normalized_ext = (ext or "txt").lower()
        mime_type = "application/json" if normalized_ext == "json" else "text/plain"
        return {
            "asset_type": "text_file",
            "format": normalized_ext,
            "mime_type": mime_type,
            "uri": path.as_uri(),
            "path": str(path),
            "source": "local_disk",
            "artifact_format": fmt,
        }

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        if fmt not in self.formats:
            raise ValueError(f"Unsupported text format for text builder: {fmt}")
        llm_out: dict[str, Any] = {}
        llm_attempted = bool(self.enable_llm and self.llm and self.llm.enabled)
        try:
            llm_out = self._generate_with_llm(fmt=fmt, ctx=ctx)
        except Exception:
            llm_out = {}
        payload = llm_out.get("payload_json") if isinstance(llm_out, dict) else None
        used_llm_payload = isinstance(payload, dict)
        merged = (
            self._merge_payload(payload=payload, fmt=fmt, ctx=ctx)
            if used_llm_payload
            else self._fallback_payload(fmt=fmt, ctx=ctx)
        )
        if isinstance(merged.get("settings"), dict):
            merged["settings"]["generation_source"] = "llm" if used_llm_payload else "fallback"
            merged["settings"]["llm_attempted"] = llm_attempted
        logger.info(
            "TextArtifactsBuilder complete: fmt=%s source=%s llm_attempted=%s",
            fmt,
            "llm" if used_llm_payload else "fallback",
            llm_attempted,
        )
        title = str((llm_out.get("title") if isinstance(llm_out, dict) else "") or "").strip()
        if not title:
            title = f"{ctx.topic_title} - {fmt.replace('_', ' ').title()}"
        tags = self._normalize_tags(llm_out.get("tags_json") if isinstance(llm_out, dict) else None, list(ctx.seed_keywords))
        text_out, ext = self._text_output_for_disk(fmt=fmt, payload=merged)
        saved_path = _save_text_to_disk(
            text_out,
            ext=ext,
            project_id=ctx.project_id,
            topic_title=ctx.topic_title,
            fmt=fmt,
        )
        if isinstance(merged.get("settings"), dict) and saved_path is not None:
            merged["settings"]["local_output_path"] = str(saved_path)
        if saved_path is not None:
            if not isinstance(merged.get("assets"), list):
                merged["assets"] = []
            merged["assets"].append(self._local_text_asset(path=saved_path, ext=ext, fmt=fmt))
        return ArtifactDraft(format=fmt, title=title, payload_json=merged, tags_json=tags)


BUILDER = TextArtifactsBuilder()
