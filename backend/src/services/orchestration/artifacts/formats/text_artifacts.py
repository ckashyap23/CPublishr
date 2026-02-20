from __future__ import annotations

import json
from typing import Any

from src.core.config import settings
from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext


TEXT_FORMATS = {
    "caption",
    "x_post",  # post
    "newsletter",
    "blog_long",  # blog
    "script_short",  # script
    "cta_variants",  # cta
}


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
        return parse_json_object(raw) or {}

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

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        if fmt not in self.formats:
            raise ValueError(f"Unsupported text format for text builder: {fmt}")
        llm_out: dict[str, Any] = {}
        try:
            llm_out = self._generate_with_llm(fmt=fmt, ctx=ctx)
        except Exception:
            llm_out = {}
        payload = llm_out.get("payload_json") if isinstance(llm_out, dict) else None
        merged = self._merge_payload(payload=payload, fmt=fmt, ctx=ctx) if isinstance(payload, dict) else self._fallback_payload(fmt=fmt, ctx=ctx)
        title = str((llm_out.get("title") if isinstance(llm_out, dict) else "") or "").strip()
        if not title:
            title = f"{ctx.topic_title} - {fmt.replace('_', ' ').title()}"
        tags = self._normalize_tags(llm_out.get("tags_json") if isinstance(llm_out, dict) else None, list(ctx.seed_keywords))
        return ArtifactDraft(format=fmt, title=title, payload_json=merged, tags_json=tags)


BUILDER = TextArtifactsBuilder()
