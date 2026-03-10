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
from src.services.orchestration.artifacts.persistence import save_text_to_local, upload_artifact_text
from src.services.storage.prompt_blob_storage import format_chat_prompt_text

logger = logging.getLogger(__name__)

TEXT_FORMATS = {
    "caption",
    "post",
    "newsletter",
    "blog",
    "script_short",
    "cta_variants",
}

BODY_FORMATS = {"caption", "post", "newsletter", "blog"}

class TextArtifactsBuilder:
    kind = "text"
    formats = set(TEXT_FORMATS)

    def __init__(self, llm: AzureOpenAIClient | None = None):
        self.llm = llm or AzureOpenAIClient()
        self.enable_llm = bool(settings.artifact_text_llm_enabled)

    # -------------------------------------------------------------------------
    # Helpers: normalization / merge
    # -------------------------------------------------------------------------
    @staticmethod
    def _clean_dict(d: dict[str, Any] | None) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if not isinstance(d, dict):
            return out
        for k, v in d.items():
            if v in (None, "", [], {}):
                continue
            if isinstance(v, str):
                v = v.strip()
                if not v:
                    continue
            out[k] = v
        return out

    @staticmethod
    def _merge_dicts(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
        """
        Shallow merge + nested dict merge.
        Used for iterate flow:
          - base: source artifact settings
          - override: ctx-provided edit overrides
        """
        out = dict(base or {})
        for k, v in (override or {}).items():
            if v is None:
                continue
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                merged = dict(out[k])
                merged.update({kk: vv for kk, vv in v.items() if vv is not None})
                out[k] = merged
            else:
                out[k] = v
        return out

    @staticmethod
    def _coerce_int(x: Any) -> int | None:
        try:
            if isinstance(x, bool):
                return None
            if isinstance(x, (int, float)):
                return int(x)
            s = str(x).strip()
            if not s:
                return None
            return int(float(s))
        except Exception:
            return None

    @staticmethod
    def _clamp(n: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, n))

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
    def _body_text_from_payload(fmt: str, payload: dict[str, Any]) -> str:
        if fmt in BODY_FORMATS:
            return str(payload.get("body") or "").strip()
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        lines = [str(it.get("text") or "").strip() for it in items if isinstance(it, dict)]
        return "\n".join([x for x in lines if x])

    @staticmethod
    def _text_output_for_disk(*, fmt: str, payload: dict[str, Any]) -> tuple[str, str]:
        if fmt in BODY_FORMATS:
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

    @staticmethod
    def _source_settings(source_payload: dict[str, Any]) -> dict[str, Any]:
        return source_payload.get("settings") if isinstance(source_payload.get("settings"), dict) else {}

    # -------------------------------------------------------------------------
    # Helpers: audience / tone / style
    # -------------------------------------------------------------------------
    @staticmethod
    def _audience_values(ctx: PipelineContext) -> tuple[str, str]:
        audience = ctx.target_audience if isinstance(ctx.target_audience, dict) else {}
        segment = str(audience.get("primary_segment") or "general").strip()
        notes = str(audience.get("notes") or "").strip() or "not specified"
        return segment, notes

    @staticmethod
    def _get_style_source(ctx: PipelineContext) -> str:
        src = getattr(ctx, "style_source", None)
        src = str(src).strip().lower() if src else ""
        return src if src in {"voice_profile", "manual"} else "manual"

    def _tone_base(self, ctx: PipelineContext) -> str:
        base = getattr(ctx, "tone_base", None)
        base = (str(base).strip().lower() if base else "").strip()
        if base in {"analytical", "professional", "conversational"}:
            return base

        pref = str(getattr(ctx, "tone_preference", "") or "").strip().lower()
        if pref in {"analytical", "professional", "conversational"}:
            return pref

        return "professional"

    def _tone_nuance(self, ctx: PipelineContext) -> dict[str, Any]:
        return self._clean_dict(getattr(ctx, "tone_nuance", None))

    def _style_context(self, ctx: PipelineContext) -> dict[str, Any]:
        """
        Prepared by orchestration/UI.
        - manual quick mode can include only {"core_voice": "..."} (+ optional)
        - voice_profile mode can include style_summary/core_voice/do/dont/exemplars
        """
        sc = self._clean_dict(getattr(ctx, "style_context", None))
        if isinstance(sc.get("exemplars"), list) and sc["exemplars"] and "exemplar_usage" not in sc:
            sc["exemplar_usage"] = "mimic_style_not_text"
        return sc

    def _sanitize_format_overrides(self, fmt: str, overrides: dict[str, Any]) -> dict[str, Any]:
        """
        Keep this lightweight: sanitize common keys + clamp obvious ranges.
        The prompt still treats overrides as hard constraints.
        """
        o = self._clean_dict(overrides)

        if "length" in o and str(o["length"]).lower() not in {"short", "medium", "long"}:
            o.pop("length", None)
        if "length_preference" in o and str(o["length_preference"]).lower() not in {"short", "medium", "long"}:
            o.pop("length_preference", None)

        if "emoji_density" in o and str(o["emoji_density"]).lower() not in {"none", "light", "moderate"}:
            o.pop("emoji_density", None)

        if "cta_strength" in o and str(o["cta_strength"]).lower() not in {"soft", "medium", "strong"}:
            o.pop("cta_strength", None)

        if "pacing" in o and str(o["pacing"]).lower() not in {"slow", "normal", "fast"}:
            o.pop("pacing", None)

        if "seo_intent" in o and str(o["seo_intent"]).lower() not in {"informational", "how-to", "comparison"}:
            o.pop("seo_intent", None)

        if "structure_hint" in o:
            s = str(o["structure_hint"]).strip()
            o["structure_hint"] = s[:240] if s else s
            if not o["structure_hint"]:
                o.pop("structure_hint", None)

        if fmt == "cta_variants":
            vc = self._coerce_int(o.get("variant_count"))
            if vc is not None:
                o["variant_count"] = self._clamp(vc, 7, 11)

            angles = o.get("angles")
            allowed = {"urgency", "curiosity", "benefit", "social-proof", "low-friction", "question"}
            if isinstance(angles, list):
                cleaned = []
                for a in angles:
                    s = str(a).strip().lower()
                    if s in allowed and s not in cleaned:
                        cleaned.append(s)
                if cleaned:
                    o["angles"] = cleaned
                else:
                    o.pop("angles", None)

        if fmt == "script_short":
            td = self._coerce_int(o.get("target_duration_sec"))
            if td is not None:
                o["target_duration_sec"] = self._clamp(td, 10, 120)

        if fmt == "newsletter":
            sections = self._coerce_int(o.get("sections"))
            if sections is not None:
                o["sections"] = self._clamp(sections, 3, 6)
            tb = self._coerce_int(o.get("takeaway_bullets"))
            if tb is not None:
                o["takeaway_bullets"] = self._clamp(tb, 3, 6)

        if fmt == "blog":
            faq = self._coerce_int(o.get("faq_count"))
            if faq is not None:
                o["faq_count"] = self._clamp(faq, 0, 5)

        return o

    def _format_overrides(self, ctx: PipelineContext, *, fmt: str) -> dict[str, Any]:
        fo = getattr(ctx, "format_overrides", None)
        if not isinstance(fo, dict):
            return {}
        entry = fo.get(fmt)
        if not isinstance(entry, dict):
            return {}
        return self._sanitize_format_overrides(fmt, entry)

    def _effective_governance_for_build(
        self,
        *,
        ctx: PipelineContext,
        fmt: str,
    ) -> dict[str, Any]:
        """
        Returns the effective style/tone governance used by build().
        This is also what gets persisted in payload.settings for reuse by iterate.
        """
        style_source = self._get_style_source(ctx)
        voice_profile_id = getattr(ctx, "voice_profile_id", None)
        tone_base = self._tone_base(ctx)
        tone_nuance = self._tone_nuance(ctx)
        style_context = self._style_context(ctx)
        format_overrides = self._format_overrides(ctx, fmt=fmt)

        return {
            "style_source": style_source,
            "voice_profile_id": str(voice_profile_id) if voice_profile_id else None,
            "tone_base": tone_base,
            "tone_nuance": tone_nuance,
            "style_context": style_context,
            "format_overrides": format_overrides,
        }

    def _effective_governance_for_edit(
        self,
        *,
        ctx: PipelineContext,
        fmt: str,
        source_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge source artifact settings + current iterate overrides.
        Precedence:
          source artifact settings  <  ctx-provided overrides
        """
        source_settings = self._source_settings(source_payload)

        base_style_source = str(source_settings.get("style_source") or "manual").strip().lower()
        if base_style_source not in {"voice_profile", "manual"}:
            base_style_source = "manual"

        base_voice_profile_id = source_settings.get("voice_profile_id")
        base_tone_base = str(source_settings.get("tone_base") or "professional").strip().lower()
        if base_tone_base not in {"analytical", "professional", "conversational"}:
            base_tone_base = "professional"

        base_tone_nuance = self._clean_dict(source_settings.get("tone_nuance"))
        base_style_context = self._clean_dict(source_settings.get("style_context"))

        source_fmt_overrides_all = source_settings.get("format_overrides") if isinstance(source_settings.get("format_overrides"), dict) else {}
        if fmt in source_fmt_overrides_all and isinstance(source_fmt_overrides_all.get(fmt), dict):
            # defensive if someone stored nested-by-format
            base_format_overrides = self._sanitize_format_overrides(fmt, source_fmt_overrides_all.get(fmt))
        else:
            base_format_overrides = self._sanitize_format_overrides(fmt, source_fmt_overrides_all)

        # Current explicit overrides from iterate request.
        # Do not treat project defaults as explicit edit-time overrides.
        style_by_kind = getattr(ctx, "style_settings_by_kind", None)
        text_kind_raw = style_by_kind.get("text") if isinstance(style_by_kind, dict) else {}
        text_kind_raw = text_kind_raw if isinstance(text_kind_raw, dict) else {}
        fmt_style_raw = getattr(ctx, "style_settings", None)
        fmt_style_raw = fmt_style_raw if isinstance(fmt_style_raw, dict) else {}

        def has_explicit(raw: dict[str, Any], key: str) -> bool:
            return key in raw and raw.get(key) not in (None, "", [], {})

        has_ctx_style_source = has_explicit(text_kind_raw, "style_source") or has_explicit(fmt_style_raw, "style_source")
        has_ctx_voice_profile_id = has_explicit(text_kind_raw, "voice_profile_id") or has_explicit(fmt_style_raw, "voice_profile_id")
        has_ctx_tone_base = (
            has_explicit(text_kind_raw, "tone_base")
            or has_explicit(fmt_style_raw, "tone_base")
            or has_explicit(text_kind_raw, "tone_preference")
            or has_explicit(fmt_style_raw, "tone_preference")
        )
        has_ctx_tone_nuance = has_explicit(text_kind_raw, "tone_nuance") or has_explicit(fmt_style_raw, "tone_nuance")
        has_ctx_style_context = (
            has_explicit(text_kind_raw, "style_context")
            or has_explicit(fmt_style_raw, "style_context")
            or has_explicit(text_kind_raw, "core_voice")
            or has_explicit(fmt_style_raw, "core_voice")
            or has_explicit(text_kind_raw, "voice_profile_preview")
            or has_explicit(fmt_style_raw, "voice_profile_preview")
            or has_explicit(text_kind_raw, "voice_profile_edits")
            or has_explicit(fmt_style_raw, "voice_profile_edits")
        )
        has_ctx_fmt_overrides = bool(self._format_overrides(ctx, fmt=fmt))

        # Current overrides from ctx (effective normalized values)
        override_style_source = self._get_style_source(ctx)
        override_voice_profile_id = getattr(ctx, "voice_profile_id", None)
        override_tone_base = self._tone_base(ctx)
        override_tone_nuance = self._tone_nuance(ctx)
        override_style_context = self._style_context(ctx)
        override_format_overrides = self._format_overrides(ctx, fmt=fmt)

        style_source = override_style_source if has_ctx_style_source else base_style_source
        voice_profile_id = str(override_voice_profile_id) if has_ctx_voice_profile_id and override_voice_profile_id else (str(base_voice_profile_id) if base_voice_profile_id else None)
        tone_base = override_tone_base if has_ctx_tone_base else base_tone_base
        tone_nuance = self._merge_dicts(base_tone_nuance, override_tone_nuance if has_ctx_tone_nuance else {})
        style_context = self._merge_dicts(base_style_context, override_style_context if has_ctx_style_context else {})
        format_overrides = self._merge_dicts(base_format_overrides, override_format_overrides if has_ctx_fmt_overrides else {})
        format_overrides = self._sanitize_format_overrides(fmt, format_overrides)

        if isinstance(style_context.get("exemplars"), list) and style_context["exemplars"] and "exemplar_usage" not in style_context:
            style_context["exemplar_usage"] = "mimic_style_not_text"

        return {
            "style_source": style_source,
            "voice_profile_id": voice_profile_id,
            "tone_base": tone_base,
            "tone_nuance": tone_nuance,
            "style_context": style_context,
            "format_overrides": format_overrides,
        }

    # -------------------------------------------------------------------------
    # Base payload settings
    # -------------------------------------------------------------------------
    def _base_settings(
        self,
        ctx: PipelineContext,
        *,
        fmt: str,
        governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        segment, notes = self._audience_values(ctx)

        gov = governance or self._effective_governance_for_build(ctx=ctx, fmt=fmt)
        style_source = str(gov.get("style_source") or "manual")
        voice_profile_id = gov.get("voice_profile_id")
        tone_base = str(gov.get("tone_base") or "professional")
        tone_nuance = self._clean_dict(gov.get("tone_nuance"))
        style_context = self._clean_dict(gov.get("style_context"))
        fmt_overrides = self._clean_dict(gov.get("format_overrides"))

        # Avoid persisting heavy exemplar blobs in payload.settings
        style_for_storage = dict(style_context)
        style_for_storage.pop("exemplars", None)

        out: dict[str, Any] = {
            "language": "en",
            "format": fmt,
            "target_audience": segment,
            "target_audience_notes": notes,
            "audience_familiarity": getattr(ctx, "audience_familiarity", None) or "somewhat_familiar",
            "detail_level": getattr(ctx, "detail_level", None) or "practical",
            "tone_base": tone_base,
            "tone_nuance": tone_nuance,
            "style_source": style_source,
            "tone_preference_project": getattr(ctx, "tone_preference", None) or "not specified",
        }

        if voice_profile_id:
            out["voice_profile_id"] = str(voice_profile_id)
        if style_for_storage:
            out["style_context"] = style_for_storage
        if fmt_overrides:
            out["format_overrides"] = fmt_overrides

        return out

    # -------------------------------------------------------------------------
    # Format rules + fallback
    # -------------------------------------------------------------------------
    @staticmethod
    def _format_rule(fmt: str) -> str:
        if fmt in BODY_FORMATS:
            return "Use payload.body (string). payload.items must be []."
        if fmt == "script_short":
            return 'Use payload.items beat objects: [{"item_type":"beat","sequence":1,"text":"..."}], body=null.'
        if fmt == "cta_variants":
            return 'Use payload.items cta objects: [{"item_type":"cta","sequence":1,"text":"..."}], body=null.'
        return "Use valid envelope fields only."

    def _fallback_payload(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        governance: dict[str, Any] | None = None,
        source_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = default_payload_template()
        payload["settings"] = self._base_settings(ctx, fmt=fmt, governance=governance)

        excerpt = (getattr(ctx, "master_body", None) or "").strip()
        if not excerpt and isinstance(source_payload, dict):
            excerpt = self._body_text_from_payload(fmt, source_payload)

        excerpt = excerpt or "not specified"

        if fmt in BODY_FORMATS:
            payload["body"] = excerpt[:1800]
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

    # -------------------------------------------------------------------------
    # LLM prompt builders
    # -------------------------------------------------------------------------
    def _build_generation_prompts(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        governance: dict[str, Any],
    ) -> tuple[str, str]:
        audience_segment, audience_notes = self._audience_values(ctx)

        style_source = str(governance.get("style_source") or "manual")
        voice_profile_id = governance.get("voice_profile_id")
        tone_base = str(governance.get("tone_base") or "professional")
        tone_nuance = self._clean_dict(governance.get("tone_nuance"))
        style_context = self._clean_dict(governance.get("style_context"))
        fmt_overrides = self._clean_dict(governance.get("format_overrides"))

        system_prompt = """
You are a senior multi-format copywriter that generates PLATFORM-AGNOSTIC artifacts:
caption, post, newsletter, blog, short scripts, CTA variants.

You MUST return exactly ONE JSON object with ONLY these top-level keys:
- "title"
- "payload_json"
- "tags_json"

No markdown fences. No extra keys. No new facts.
Use ONLY the provided inputs.

STYLE GOVERNANCE (IMPORTANT):
- Apply style_context and tone_nuance as binding constraints.
- Apply format_overrides as binding constraints too. If present, MUST follow them.
- If style_context has do_rules: MUST follow them.
- If style_context has dont_rules: MUST avoid them.
- If style_context has exemplars: imitate style only; NEVER copy exact lines.
- Manual style may only have core_voice — still obey it.

PLATFORM RULE:
- Do NOT tailor to Instagram/X/LinkedIn. Publishing/platform packaging happens later.

CRITICAL OUTPUT RULES:
1) For body formats (caption, post, newsletter, blog): payload_json.body must be directly publishable.
2) For item formats:
   - script_short -> payload_json.body must be null, payload_json.items must contain ONLY beat objects.
   - cta_variants -> payload_json.body must be null, payload_json.items must contain ONLY cta objects.
3) Do NOT include internal planning labels in publishable text (Hook, Section, CTA, Outline, Beat, Framework, Notes, Hashtags:).
4) If you need scaffolding, place it only in payload_json.prompts[] (internal only).
5) Enforce format constraints exactly (length/structure). Rewrite shorter if needed.
6) JSON must be valid and parseable.
""".strip()

        user_prompt = f"""
Create one artifact for format="{fmt}".

STYLE SOURCE:
- style_source: {style_source}
- voice_profile_id: {voice_profile_id or "null"}

INPUTS (do not invent anything beyond these):
topic_title: {getattr(ctx, "topic_title", "")}
core_idea: {getattr(ctx, "core_idea", "")}
master_body (may be long; extract only what helps): {(getattr(ctx, "master_body", "") or "")[:6000]}
seed_keywords: {json.dumps(getattr(ctx, "seed_keywords", []) or [], ensure_ascii=False)}
target_audience: {audience_segment}
target_audience_notes: {audience_notes}
audience_familiarity: {getattr(ctx, "audience_familiarity", None) or "not specified"}
detail_level: {getattr(ctx, "detail_level", None) or "not specified"}

TONE:
tone_base (from project): {tone_base}
tone_nuance: {json.dumps(tone_nuance or {{}}, ensure_ascii=False)}

STYLE CONTEXT:
style_context: {json.dumps(style_context or {{}}, ensure_ascii=False)}

FORMAT OVERRIDES (HARD constraints; MUST follow if present):
format_overrides: {json.dumps(fmt_overrides or {{}}, ensure_ascii=False)}

INTERPRETING TONE_NUANCE:
- directness: higher => fewer qualifiers, more decisive phrasing
- warmth: higher => more human/encouraging phrasing
- energy: higher => punchier rhythm, more momentum
- authority: higher => more confident framing, fewer "maybe"

Base-tone specific keys (if present) should be honored:
- Analytical: rigor, abstraction, framework_mode
- Professional: formality, diplomacy, executive_brevity
- Conversational: humor, storyness/story_ness, relatability

FORMAT_OVERRIDES INTERPRETATION (treat as HARD constraints):
Common keys:
- length / length_preference:
  - short => compress; fewer lines/paras; minimal qualifiers.
  - medium => default constraints.
  - long => expand within the format's allowable range (never exceed hard bounds).
- emoji_density: none|light|moderate => adjust emoji usage accordingly (never use emojis if "none").
- structure_hint: obey the requested structure (e.g., framework-led, story-led, list-led, mini-story).

- cta_strength: soft|medium|strong => controls BOTH inclusion + intensity of CTA:
  IMPORTANT:
  - For BODY formats (caption/post/newsletter/blog), CTA should be embedded in payload_json.body,
    NOT as separate CTA objects.
  - If cta_strength is present and format is a BODY format, you MUST include an in-body CTA line
    (or 1-2 lines) in payload_json.body.
  - soft: gentle invite or question, no pressure.
  - medium: clear next step + benefit.
  - strong: direct ask + urgency/next step (imperative).

Format-specific keys:
- script_short:
  - target_duration_sec => roughly scale word count:
    15s ~ 40-70 words; 30s ~ 90-140; 45s ~ 140-200; 60s ~ 180-260 (adjust for pacing)
  - pacing: slow|normal|fast => change sentence length and beat density
  - If cta_strength is present: final beat CTA intensity must match (soft/medium/strong).
- newsletter:
  - sections (3-6) => use that many meaningful headings
  - takeaway_bullets (3-6) => use that many bullets in the takeaway list
  - Newsletter MUST include one clear CTA regardless; if cta_strength is present, match intensity.
- blog:
  - seo_intent: informational|how-to|comparison => reflect in headings + examples
  - faq_count (0-5) => include exactly that many Q&As (0 means omit FAQ section)
  - If cta_strength is present: include CTA in the conclusion and match intensity.
- cta_variants:
  - variant_count (7-11) => output exactly that many CTAs
  - angles => ensure CTAs cover those angles (plus optional variety)
  - If cta_strength is present: keep the whole set aligned to that intensity.

HASHTAG POLICY:
- Default: do not put hashtags in the body.
- If format_overrides/style_context requests hashtags, put them in tags_json, not body.

FORMAT CONSTRAINTS (hard rules):

- caption:
- 1 strong opening line (<= 140 chars) that stands alone.
- Total length: 400-1,000 chars (if inputs are thin, 250-500).
- 2-5 short paragraphs max; line breaks allowed.
- Emojis: optional, light (0-6 total) unless overridden.
- No hashtags in body.
- CTA behavior:
  - CTA is optional UNLESS cta_strength is present.
  - If cta_strength is present: include CTA as the FINAL line in the body matching that intensity.

- post:
- Platform-neutral short-form post.
- Default length: 600-1,600 chars (unless overridden).
- Structure: hook line, blank line, 3-8 short lines/paras.
- No threads. No "carousel slide" language unless explicitly requested via overrides.
- CTA behavior:
  - CTA is optional UNLESS cta_strength is present.
  - If cta_strength is present: include CTA as the FINAL 1-2 lines matching that intensity.

- newsletter:
- Email-style newsletter.
- title: email subject line (<= 60 chars).
- body must include:
  - warm opening line
  - 3-6 short sections with meaningful headings
  - one practical takeaway list (3-6 bullets)
  - friendly sign-off + one clear CTA
- Length: 450-900 words. No hashtags in body.
- CTA behavior:
  - CTA is REQUIRED (already).
  - If cta_strength is present: make the CTA match the requested intensity.

- blog:
- Website blog post.
- title: blog title (60-90 chars preferred).
- body must include:
  - strong intro (2-4 short paragraphs)
  - 5-8 meaningful headings
  - at least one example / case / step-by-step section
  - one bullet list (4-8 bullets)
  - short FAQ (3-5 Q&As) unless faq_count=0
  - conclusion + CTA
- Length: 1,200-2,000 words unless overridden. No hashtags in body.
- CTA behavior:
  - CTA is REQUIRED in the conclusion (already).
  - If cta_strength is present: make the CTA match the requested intensity.

- script_short:
- payload_json.body MUST be null.
- payload_json.items MUST contain beat objects only:
  {{"item_type":"beat","sequence":1,"text":"..."}}
- Beats must be speakable, natural, no internal labels.
- Hook in first 1-2 beats, CTA in final beat.
- If cta_strength is present: final beat CTA must match intensity.

- cta_variants:
- payload_json.body MUST be null.
- payload_json.items MUST contain 7-11 CTA objects only:
  {{"item_type":"cta","sequence":1,"text":"..."}}
- Each CTA: 6-18 words.
- Vary angle: urgency / curiosity / benefit / social proof / low-friction / question.
- If cta_strength is present: keep wording aligned to intensity (soft vs strong).

Shape rule (internal blueprint):
{self._format_rule(fmt)}

Return JSON in this envelope shape for payload_json:
{{
  "version": "1.0",
  "body": null,
  "items": [],
  "assets": [],
  "prompts": [],
  "settings": {{"format": "{fmt}"}},
  "notes": null
}}

tags_json guidelines:
- tags_json MUST be a flat list of strings.
- Default: topic phrases + keywords (platform-neutral).
- You MAY include hashtags in tags_json if requested via style_context/format_overrides.
""".strip()

        return system_prompt, user_prompt

    def _build_edit_prompts(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        source_payload: dict[str, Any],
        source_artifact: dict[str, Any],
        edit_instruction: str,
        governance: dict[str, Any],
    ) -> tuple[str, str]:
        audience_segment, audience_notes = self._audience_values(ctx)
        style_source = str(governance.get("style_source") or "manual")
        voice_profile_id = governance.get("voice_profile_id")
        tone_base = str(governance.get("tone_base") or "professional")
        tone_nuance = self._clean_dict(governance.get("tone_nuance"))
        style_context = self._clean_dict(governance.get("style_context"))
        fmt_overrides = self._clean_dict(governance.get("format_overrides"))

        base_text = self._body_text_from_payload(fmt, source_payload)
        source_title = str(source_artifact.get("title") or "").strip()
        source_tags = self._normalize_tags(source_artifact.get("tags_json"), [])

        system_prompt = """
You are a senior editorial rewrite assistant for structured text artifacts.

Your task is to ITERATE an existing artifact by applying the new edit instruction,
while preserving factual fidelity to the supplied source content.

You MUST return exactly ONE JSON object with ONLY these top-level keys:
- "title"
- "payload_json"
- "tags_json"

No markdown fences. No extra keys. No new unsupported facts.

EDITING RULES:
- Preserve the underlying truth/claims from the source content unless the edit instruction explicitly asks to remove, compress, expand, or reframe them.
- Apply the new edit instruction as the highest-priority change request.
- Apply tone_nuance, style_context, and format_overrides as binding constraints.
- If style_context has do_rules: MUST follow them.
- If style_context has dont_rules: MUST avoid them.
- If style_context has exemplars: imitate style only; NEVER copy exact lines.
- Preserve the same artifact format and output shape.
- Improve wording, structure, tone, pacing, and CTA intensity as requested, but keep the output directly publishable.

CRITICAL OUTPUT RULES:
1) For body formats (caption, post, newsletter, blog): payload_json.body must be directly publishable and payload_json.items must be [].
2) For item formats:
   - script_short -> payload_json.body must be null, payload_json.items must contain ONLY beat objects.
   - cta_variants -> payload_json.body must be null, payload_json.items must contain ONLY cta objects.
3) Do NOT include internal planning labels in publishable text.
4) If you need scaffolding, place it only in payload_json.prompts[] (internal only).
5) JSON must be valid and parseable.
""".strip()

        user_prompt = f"""
Iterate the existing artifact for format="{fmt}".

SOURCE ARTIFACT TITLE:
{source_title or "not specified"}

SOURCE TAGS:
{json.dumps(source_tags, ensure_ascii=False)}

SOURCE CONTENT (primary truth source):
{base_text or "not specified"}

NEW EDIT INSTRUCTION (HIGHEST PRIORITY):
{edit_instruction}

INPUT CONTEXT (do not invent beyond this):
topic_title: {getattr(ctx, "topic_title", "")}
core_idea: {getattr(ctx, "core_idea", "")}
master_body (may be long; use only if helpful and consistent): {(getattr(ctx, "master_body", "") or "")[:6000]}
seed_keywords: {json.dumps(getattr(ctx, "seed_keywords", []) or [], ensure_ascii=False)}
target_audience: {audience_segment}
target_audience_notes: {audience_notes}
audience_familiarity: {getattr(ctx, "audience_familiarity", None) or "not specified"}
detail_level: {getattr(ctx, "detail_level", None) or "not specified"}

STYLE SOURCE:
- style_source: {style_source}
- voice_profile_id: {voice_profile_id or "null"}

TONE:
tone_base: {tone_base}
tone_nuance: {json.dumps(tone_nuance or {{}}, ensure_ascii=False)}

STYLE CONTEXT:
style_context: {json.dumps(style_context or {{}}, ensure_ascii=False)}

FORMAT OVERRIDES (HARD constraints):
format_overrides: {json.dumps(fmt_overrides or {{}}, ensure_ascii=False)}

EDITING GUIDANCE:
- Rewrite the source artifact instead of writing from scratch unless the instruction clearly demands a major reframe.
- Keep the same format family and obey the same structural rules as the source format.
- If the source is weak, improve clarity and flow while staying faithful.
- If the instruction asks for a tone/style shift, apply it strongly but safely.

FORMAT RULE:
{self._format_rule(fmt)}

Return JSON in this payload_json envelope shape:
{{
  "version": "1.0",
  "body": null,
  "items": [],
  "assets": [],
  "prompts": [],
  "settings": {{"format": "{fmt}"}},
  "notes": null
}}

tags_json:
- Keep relevant source tags unless the edit naturally changes positioning.
- tags_json MUST be a flat list of strings.
""".strip()

        return system_prompt, user_prompt

    # -------------------------------------------------------------------------
    # LLM calls
    # -------------------------------------------------------------------------
    def _run_llm_json(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 1800) -> dict[str, Any]:
        if not (self.enable_llm and self.llm and self.llm.enabled):
            return {}
        raw = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=max_tokens,
        )
        parsed = parse_json_object(raw) or {}
        if not parsed:
            logger.warning(
                "TextArtifactsBuilder LLM returned unparseable JSON: chars=%s preview=%r",
                len(raw or ""),
                (raw or "")[:240],
            )
        return parsed

    def _generate_with_llm(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        governance: dict[str, Any],
    ) -> tuple[dict[str, Any], str, str]:
        if not (self.enable_llm and self.llm and self.llm.enabled):
            return {}, "", ""

        system_prompt, user_prompt = self._build_generation_prompts(fmt=fmt, ctx=ctx, governance=governance)

        parsed = self._run_llm_json(system_prompt=system_prompt, user_prompt=user_prompt)
        return parsed, system_prompt, user_prompt

    def _edit_with_llm(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        source_payload: dict[str, Any],
        source_artifact: dict[str, Any],
        edit_instruction: str,
        governance: dict[str, Any],
    ) -> tuple[dict[str, Any], str, str]:
        if not (self.enable_llm and self.llm and self.llm.enabled):
            return {}, "", ""

        system_prompt, user_prompt = self._build_edit_prompts(
            fmt=fmt,
            ctx=ctx,
            source_payload=source_payload,
            source_artifact=source_artifact,
            edit_instruction=edit_instruction,
            governance=governance,
        )

        parsed = self._run_llm_json(system_prompt=system_prompt, user_prompt=user_prompt)
        return parsed, system_prompt, user_prompt

    # -------------------------------------------------------------------------
    # Merge + normalize output
    # -------------------------------------------------------------------------
    def _merge_payload(
        self,
        *,
        payload: dict[str, Any] | None,
        fmt: str,
        ctx: PipelineContext,
        governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        merged = default_payload_template()
        if isinstance(payload, dict):
            merged.update(payload)

        if not isinstance(merged.get("settings"), dict):
            merged["settings"] = {}

        base = self._base_settings(ctx, fmt=fmt, governance=governance)
        for k, v in base.items():
            merged["settings"].setdefault(k, v)

        if fmt in BODY_FORMATS:
            if not isinstance(merged.get("body"), str) or not str(merged.get("body")).strip():
                merged["body"] = "not specified"
            merged["items"] = []
        else:
            merged["body"] = None
            if not isinstance(merged.get("items"), list):
                merged["items"] = []

            item_type = "beat" if fmt == "script_short" else "cta"
            normalized_items: list[dict[str, Any]] = []
            for idx, item in enumerate(merged.get("items") or []):
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                normalized_items.append(
                    {
                        "item_type": item_type,
                        "sequence": idx + 1,
                        "text": text,
                    }
                )
            merged["items"] = normalized_items

        merged.pop("keywords", None)
        merged.pop("tags_json", None)
        return merged

    # -------------------------------------------------------------------------
    # File / blob persistence
    # -------------------------------------------------------------------------
    def _persist_text_artifact(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        merged: dict[str, Any],
        target_artifact_id: str | None = None,
    ) -> dict[str, Any]:
        text_out, ext = self._text_output_for_disk(fmt=fmt, payload=merged)

        saved_path = save_text_to_local(
            text=text_out,
            ext=ext,
            project_id=str(getattr(ctx, "project_id", "") or ""),
            topic_title=str(getattr(ctx, "topic_title", "") or ""),
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
        upload_artifact_id = str(target_artifact_id or "").strip() or artifact_key

        blob_ref = upload_artifact_text(
            text=text_out,
            user_id=getattr(ctx, "user_id", ""),
            project_id=getattr(ctx, "project_id", ""),
            fmt=fmt,
            artifact_id=upload_artifact_id,
            filename=file_name,
            content_type=content_type,
        )

        merged["assets"] = []
        if saved_path is not None:
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

        return merged

    # -------------------------------------------------------------------------
    # Public build()
    # -------------------------------------------------------------------------
    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        fmt = (fmt or "").strip()
        if fmt not in self.formats:
            raise ValueError(f"Unsupported text format for text builder: {fmt}")

        governance = self._effective_governance_for_build(ctx=ctx, fmt=fmt)
        llm_attempted = bool(self.enable_llm and self.llm and self.llm.enabled)

        llm_out: dict[str, Any] = {}
        llm_system_prompt = ""
        llm_user_prompt = ""
        try:
            llm_out, llm_system_prompt, llm_user_prompt = self._generate_with_llm(
                fmt=fmt,
                ctx=ctx,
                governance=governance,
            )
        except Exception:
            llm_out = {}
            llm_system_prompt = ""
            llm_user_prompt = ""

        payload = llm_out.get("payload_json") if isinstance(llm_out, dict) else None
        used_llm_payload = isinstance(payload, dict)

        merged = (
            self._merge_payload(payload=payload, fmt=fmt, ctx=ctx, governance=governance)
            if used_llm_payload
            else self._fallback_payload(fmt=fmt, ctx=ctx, governance=governance)
        )

        if isinstance(merged.get("settings"), dict):
            merged["settings"]["generation_source"] = "llm" if used_llm_payload else "fallback"
            merged["settings"]["llm_attempted"] = llm_attempted

        if llm_system_prompt or llm_user_prompt:
            merged_prompts = merged.get("prompts") if isinstance(merged.get("prompts"), list) else []
            merged_prompts = [p for p in merged_prompts if isinstance(p, dict)]
            merged_prompts.insert(
                0,
                {
                    "name": "artifact_prompt",
                    "text": format_chat_prompt_text(system_prompt=llm_system_prompt, user_prompt=llm_user_prompt),
                    "tool": "azure_openai",
                },
            )
            merged["prompts"] = merged_prompts

        logger.info(
            "TextArtifactsBuilder complete: fmt=%s source=%s llm_attempted=%s",
            fmt,
            "llm" if used_llm_payload else "fallback",
            llm_attempted,
        )

        custom_title = ""
        if isinstance(getattr(ctx, "style_settings", None), dict):
            custom_title = str(ctx.style_settings.get("default_artifact_title") or "").strip()

        title = custom_title
        if not title:
            title = str((llm_out.get("title") if isinstance(llm_out, dict) else "") or "").strip()
        if not title:
            title = f"{getattr(ctx, 'topic_title', '')} - {fmt.replace('_', ' ').title()}".strip(" -")
        if custom_title and len(getattr(ctx, "requested_formats", []) or []) > 1:
            title = f"{custom_title} - {fmt.replace('_', ' ').title()}"

        tags = self._normalize_tags(
            llm_out.get("tags_json") if isinstance(llm_out, dict) else None,
            list(getattr(ctx, "seed_keywords", []) or []),
        )

        merged = self._persist_text_artifact(fmt=fmt, ctx=ctx, merged=merged)

        return ArtifactDraft(format=fmt, title=title, payload_json=merged, tags_json=tags)

    # -------------------------------------------------------------------------
    # Public edit()
    # -------------------------------------------------------------------------
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
        _ = source_blob_paths  # text iterate edits derive from source payload content.
        fmt = (fmt or "").strip()
        if fmt not in self.formats:
            raise ValueError(f"Unsupported text format for text builder edit: {fmt}")

        cleaned_instruction = str(edit_instruction or "").strip()
        if not cleaned_instruction:
            raise ValueError("edit_instruction is required")

        source_payload = source_artifact.get("payload_json") if isinstance(source_artifact, dict) else {}
        source_payload = source_payload if isinstance(source_payload, dict) else {}

        governance = self._effective_governance_for_edit(
            ctx=ctx,
            fmt=fmt,
            source_payload=source_payload,
        )

        llm_attempted = bool(self.enable_llm and self.llm and self.llm.enabled)
        llm_out: dict[str, Any] = {}
        try:
            llm_out, system_prompt, user_prompt = self._edit_with_llm(
                fmt=fmt,
                ctx=ctx,
                source_payload=source_payload,
                source_artifact=source_artifact,
                edit_instruction=cleaned_instruction,
                governance=governance,
            )
        except Exception:
            llm_out = {}
            system_prompt = ""
            user_prompt = ""

        payload = llm_out.get("payload_json") if isinstance(llm_out, dict) else None
        used_llm_payload = isinstance(payload, dict)

        merged = (
            self._merge_payload(payload=payload, fmt=fmt, ctx=ctx, governance=governance)
            if used_llm_payload
            else self._fallback_payload(
                fmt=fmt,
                ctx=ctx,
                governance=governance,
                source_payload=source_payload,
            )
        )

        # If LLM failed, preserve original content shape instead of generic fallback when source exists
        if not used_llm_payload and source_payload:
            merged = self._merge_payload(payload=source_payload, fmt=fmt, ctx=ctx, governance=governance)

        # Prompt audit trail
        iterate_prompt_snapshot = (
            format_chat_prompt_text(system_prompt=system_prompt, user_prompt=user_prompt)
            if system_prompt or user_prompt
            else (
                f"EDIT INSTRUCTION:\n{cleaned_instruction}\n\n"
                f"SOURCE CONTENT:\n{self._body_text_from_payload(fmt, source_payload) or 'not specified'}\n"
            )
        )

        merged["prompts"] = [
            {"name": "iterate_instruction", "text": cleaned_instruction, "tool": "user"},
            {"name": "iterate_prompt", "text": iterate_prompt_snapshot, "tool": "azure_openai"},
        ]

        if isinstance(merged.get("settings"), dict):
            merged["settings"]["generation_source"] = "iterate_edit"
            merged["settings"]["llm_attempted"] = llm_attempted
            merged["settings"]["edit_instruction"] = cleaned_instruction
            merged["settings"]["source_artifact_id"] = str(
                source_artifact.get("artifact_id") or source_artifact.get("id") or ""
            ).strip() or None

        tags = self._normalize_tags(
            llm_out.get("tags_json") if isinstance(llm_out, dict) else None,
            self._normalize_tags(
                source_artifact.get("tags_json") if isinstance(source_artifact, dict) else None,
                list(getattr(ctx, "seed_keywords", []) or []),
            ),
        )

        title = str((llm_out.get("title") if isinstance(llm_out, dict) else "") or "").strip()
        if not title:
            title = str(source_artifact.get("title") or "").strip() if isinstance(source_artifact, dict) else ""
        if not title:
            title = f"{getattr(ctx, 'topic_title', '')} - {fmt.replace('_', ' ').title()}".strip(" -")

        merged = self._persist_text_artifact(
            fmt=fmt,
            ctx=ctx,
            merged=merged,
            target_artifact_id=target_artifact_id,
        )

        return ArtifactDraft(format=fmt, title=title, payload_json=merged, tags_json=tags, status="generated")


BUILDER = TextArtifactsBuilder()
