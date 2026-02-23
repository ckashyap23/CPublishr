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
from src.services.storage.artifact_blob_storage import upload_text

TEXT_DIR = Path(__file__).resolve().parent / "text"
logger = logging.getLogger(__name__)


TEXT_FORMATS = {
    "instagram_caption",
    "x_post",  # post
    "linkedin_post",
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
        if fmt in {"instagram_caption", "x_post", "linkedin_post", "blog_long", "newsletter"}:
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
        if fmt in {"instagram_caption", "x_post", "linkedin_post", "blog_long", "newsletter"}:
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
You are a senior multi-format copywriter (Instagram, X, LinkedIn, newsletters, blogs, scripts, CTAs).

You MUST return exactly ONE JSON object with ONLY these top-level keys:
- "title"
- "payload_json"
- "tags_json"

No markdown fences. No extra keys. No new facts.
Use ONLY the provided inputs (topic_title/core_idea/master_body/seed_keywords/audience/style_settings).

CRITICAL OUTPUT RULES:
1) For body-based formats, payload_json.body must be directly publishable text.
   For item-based formats (script_short, cta_variants), payload_json.items must contain the publishable output and payload_json.body must be null.
2) Do NOT include internal planning labels in publishable text (Hook, Section, CTA, Outline, Beat, Framework, Angle, Notes, Hashtags:).
3) If you need scaffolding, place it only in payload_json.prompts[] (internal only).
4) Enforce format constraints exactly (length/structure/hashtag rules). Rewrite shorter if needed.
5) JSON must be valid and parseable.
""".strip()

        user_prompt = f"""
Create one text artifact for format={fmt}.

INPUTS (do not invent anything beyond these):
topic_title: {ctx.topic_title}
core_idea: {ctx.core_idea}
master_body (may be long; extract only what helps): {ctx.master_body[:6000]}
seed_keywords: {json.dumps(ctx.seed_keywords, ensure_ascii=False)}
target_audience: {audience_segment}
target_audience_notes: {audience_notes}
audience_familiarity: {ctx.audience_familiarity or "not specified"}
detail_level: {ctx.detail_level or "not specified"}
tone_preference: {ctx.tone_preference or "not specified"}
style_settings: {json.dumps(ctx.style_settings or {}, ensure_ascii=False)}

FORMAT CONSTRAINTS (hard rules):

- instagram_caption:
- 1 strong opening line (<= 125 chars) that stands alone.
- Total length: 600-1,200 chars (if inputs are thin, 300-600).
- 2-4 short paragraphs max; line breaks allowed.
- Emojis: light (0-6 total), optional.
- Hashtags: 5-10 at the very end, no "Hashtags:" label.

- x_post:
- Single post only (NOT a thread).
- Total length: <= 260 chars.
- Hashtags: 0-2 max, no label.
- One punchy idea + optional CTA/question. No multi-section formatting.

- linkedin_post:
- Total length: 600-1,600 chars.
- Structure: hook line, blank line, 3-6 short paras/lines, optional CTA.
- Hashtags: 3-5 at the end, no label.
- Professional, insight-forward, not Twitter slang.

- newsletter:
- Email-style newsletter edition.
- title: email subject line (<= 60 chars).
- payload_json.body:
  - warm opening line (no placeholders unless provided)
  - 3-6 short sections with meaningful headings (not "Section 1/2")
  - one practical takeaway list (3-6 bullets)
  - friendly sign-off + one clear CTA
- Length: 450-900 words.
- No hashtags in body.

- blog_long:
- Long-form blog post for a website.
- title: blog title (60-90 chars preferred).
- payload_json.body:
  - strong intro (2-4 short paragraphs)
  - 5-8 meaningful headings (not "Section"/"Part 1")
  - at least one example/case/step-by-step section
  - one bullet list (4-8 bullets)
  - one short FAQ (3-5 Q&As)
  - conclusion + CTA
- Length: 1,200-2,000 words (unless detail_level says otherwise).
- No hashtags in body.

- script_short:
- payload_json.body MUST be null.
- payload_json.items MUST contain beat objects only:
  - {{"item_type":"beat","sequence":1,"text":"..."}}
- Beat text must be speakable, natural, no internal labels.
- Include opening hook in first 1-2 beats and CTA in final beat.
- Total script target: about 110-150 words (allow 150-180 if fast pacing is requested).

- cta_variants:
- payload_json.body MUST be null.
- payload_json.items MUST contain 7-11 CTA objects only:
  - {{"item_type":"cta","sequence":1,"text":"..."}}
- Each CTA: 6-18 words.
- Vary angle: urgency / curiosity / benefit / social proof / low-friction / question.
- No hashtags unless explicitly appropriate.

IMPORTANT ABOUT THE SHAPE RULE:
- The Shape rule is an internal blueprint.
- Do NOT copy blueprint labels into publishable text.

Shape rule (internal blueprint):
{self._format_rule(fmt)}

Return JSON in this envelope shape for payload_json (respect format-specific body/items rules):
{{
  "version": "1.0",
  "body": null,
  "items": [],
  "assets": [],
  "prompts": [],
  "settings": {{"format": "{fmt}"}},
  "notes": null
}}

tags_json guidelines (IMPORTANT: tags_json MUST be a flat list of strings, not an object):
- For instagram_caption, linkedin_post, x_post: prefer hashtags in tags_json.
- For blog_long and newsletter: prefer topic phrases and SEO keyword phrases in tags_json (no hashtags).
- If the format does not naturally use hashtags/topics, fall back to plain keywords.
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
        if fmt in {"instagram_caption", "x_post", "linkedin_post", "blog_long", "newsletter"}:
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
        if fmt in {"instagram_caption", "x_post", "linkedin_post", "blog_long", "newsletter"}:
            body = payload.get("body")
            return (str(body) if body is not None else "", "txt")
        return (json.dumps(payload, ensure_ascii=False, indent=2), "json")

    @staticmethod
    def _local_text_asset(
        *,
        path: Path,
        ext: str,
        fmt: str,
        uri_override: str | None = None,
        blob_path: str | None = None,
    ) -> dict[str, Any]:
        normalized_ext = (ext or "txt").lower()
        mime_type = "application/json" if normalized_ext == "json" else "text/plain"
        return {
            "asset_type": "text_file",
            "format": normalized_ext,
            "mime_type": mime_type,
            "uri": uri_override or path.as_uri(),
            "path": str(path),
            "blob_path": blob_path,
            "source": "azure_blob" if blob_path else "local_disk",
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
            file_name = saved_path.name
            artifact_key = saved_path.stem
        else:
            file_name = f"{fmt}_{int(time.time() * 1000)}.{ext}"
            artifact_key = Path(file_name).stem
        content_type = "application/json" if ext.lower() == "json" else "text/plain; charset=utf-8"
        blob_ref = upload_text(
            text=text_out,
            user_id=ctx.user_id,
            project_id=ctx.project_id,
            format=fmt,
            artifact_id=artifact_key,
            filename=file_name,
            content_type=content_type,
        )
        if saved_path is not None:
            if not isinstance(merged.get("assets"), list):
                merged["assets"] = []
            merged["assets"].append(
                self._local_text_asset(
                    path=saved_path,
                    ext=ext,
                    fmt=fmt,
                    uri_override=(blob_ref or {}).get("uri"),
                    blob_path=(blob_ref or {}).get("blob_path"),
                )
            )
        elif blob_ref:
            if not isinstance(merged.get("assets"), list):
                merged["assets"] = []
            merged["assets"].append(
                {
                    "asset_type": "text_file",
                    "format": ext.lower(),
                    "mime_type": "application/json" if ext.lower() == "json" else "text/plain",
                    "uri": blob_ref["uri"],
                    "path": None,
                    "blob_path": blob_ref.get("blob_path"),
                    "source": "azure_blob",
                    "artifact_format": fmt,
                }
            )
        return ArtifactDraft(format=fmt, title=title, payload_json=merged, tags_json=tags)


BUILDER = TextArtifactsBuilder()
