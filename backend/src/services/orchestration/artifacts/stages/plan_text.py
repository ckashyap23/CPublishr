from __future__ import annotations

import json
from typing import Any

from src.core.config import settings
from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext, StageResult


TEXT_FORMATS = {
    "caption",
    "x_post",
    "x_thread",
    "blog_short",
    "blog_long",
    "newsletter",
    "script_short",
    "script_long",
    "hook_bank",
    "headline_variants",
    "cta_variants",
    "faq",
    "playbook",
}


class PlanTextStage:
    name = "plan"

    def __init__(self, llm: AzureOpenAIClient | None = None):
        self.llm = llm or AzureOpenAIClient()
        # Explicit opt-in to avoid unexpected network calls in tests/dev.
        self.enable_llm = bool(settings.artifact_text_llm_enabled)

    # -----------------------------
    # Settings / payload utilities
    # -----------------------------
    @staticmethod
    def _base_settings(ctx: PipelineContext) -> dict[str, Any]:
        settings: dict[str, Any] = {
            "language": "en",
            "tone": ctx.tone_preference or "professional",
            "depth": ctx.content_depth or "intermediate",
            "target_audience": ctx.target_audience or "not specified",
        }
        if isinstance(ctx.style_settings, dict):
            # Style settings are allowed to override/extend but should remain a dict.
            settings.update(ctx.style_settings)
        return settings

    @staticmethod
    def _format_spec(fmt: str) -> dict[str, Any]:
        """
        Compact, format-aware spec that drives both prompting and validation.
        """
        if fmt == "caption":
            return {"shape": "body", "length": "80-180 words", "notes": "Hook + value + close. Max 1 emoji."}
        if fmt == "x_post":
            return {"shape": "body", "length": "1 post <= 260 chars", "notes": "Punchy. No hashtags."}
        if fmt == "x_thread":
            return {"shape": "items(tweet)", "count": "6-10", "notes": "Tweet 1 hook; last tweet CTA."}
        if fmt == "blog_short":
            return {"shape": "body", "length": "450-750 words", "notes": "Skimmable headings + bullets."}
        if fmt == "blog_long":
            return {"shape": "body", "length": "900-1400 words", "notes": "Add 2 examples + pitfalls."}
        if fmt == "newsletter":
            return {"shape": "body", "length": "500-900 words", "notes": "Friendly professional. 3 sections."}
        if fmt == "script_short":
            return {"shape": "items(beat)", "duration_sec": 30, "notes": "Fast pacing. 7-12 beats."}
        if fmt == "script_long":
            return {"shape": "items(beat)", "duration_sec": 120, "notes": "Clear arcs. 18-28 beats."}
        if fmt == "hook_bank":
            return {"shape": "items(hook)", "count": "15-25", "notes": "Diverse hooks, no repeats."}
        if fmt == "headline_variants":
            return {"shape": "items(headline)", "count": "10-15", "notes": "Short, high-signal."}
        if fmt == "cta_variants":
            return {"shape": "items(cta)", "count": "10-15", "notes": "Actionable. Avoid spammy tone."}
        if fmt == "faq":
            return {"shape": "items(qa)", "count": "6-10", "notes": "Questions users would ask. Crisp answers."}
        if fmt == "playbook":
            return {"shape": "items(step)", "count": "7-12", "notes": "Steps with title + text; practical."}
        return {"shape": "body", "length": "not specified", "notes": "not specified"}

    def _fallback_payload(self, *, fmt: str, ctx: PipelineContext) -> dict[str, Any]:
        """
        Deterministic fallback that always satisfies the envelope and basic format shapes,
        so the pipeline never breaks.
        """
        payload = default_payload_template()
        payload["settings"] = self._base_settings(ctx)

        excerpt = (ctx.master_body or "not specified").strip()

        if fmt in {"caption", "x_post", "blog_short", "blog_long", "newsletter"}:
            payload["body"] = excerpt[:1800] if excerpt else "not specified"
            payload["items"] = []
        elif fmt == "x_thread":
            payload["body"] = None
            payload["items"] = [
                {"item_type": "tweet", "sequence": 1, "text": (excerpt[:240] or "not specified")},
                {"item_type": "tweet", "sequence": 2, "text": "not specified"},
            ]
        elif fmt in {"script_short", "script_long"}:
            payload["body"] = None
            payload["items"] = [
                {"item_type": "beat", "sequence": 1, "text": "not specified"},
                {"item_type": "beat", "sequence": 2, "text": "not specified"},
            ]
            payload["settings"]["target_duration_sec"] = 30 if fmt == "script_short" else 120
        elif fmt in {"hook_bank", "headline_variants", "cta_variants"}:
            payload["body"] = None
            item_type = "hook" if fmt == "hook_bank" else ("headline" if fmt == "headline_variants" else "cta")
            payload["items"] = [
                {"item_type": item_type, "sequence": 1, "text": "not specified"},
                {"item_type": item_type, "sequence": 2, "text": "not specified"},
            ]
        elif fmt == "faq":
            payload["body"] = None
            payload["items"] = [{"item_type": "qa", "sequence": 1, "title": "not specified", "text": "not specified"}]
        elif fmt == "playbook":
            payload["body"] = None
            payload["items"] = [{"item_type": "step", "sequence": 1, "title": "not specified", "text": "not specified"}]

        return payload

    # -----------------------------
    # Validation / normalization
    # -----------------------------
    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(str(value).strip())
        except Exception:
            return int(default)

    @staticmethod
    def _dedupe_keep_order(xs: list[str]) -> list[str]:
        out: list[str] = []
        seen = set()
        for x in xs:
            x = (x or "").strip()
            if not x:
                continue
            key = x.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(x)
        return out

    def _merge_and_normalize_payload(self, *, raw_payload: dict[str, Any] | None, fmt: str, ctx: PipelineContext) -> dict[str, Any]:
        """
        Enforce the universal envelope keys and merge base settings safely.
        """
        merged = default_payload_template()
        if isinstance(raw_payload, dict):
            merged.update(raw_payload)

        # Ensure required keys exist and have correct types
        if not isinstance(merged.get("items"), list):
            merged["items"] = []
        if not isinstance(merged.get("assets"), list):
            merged["assets"] = []
        if not isinstance(merged.get("prompts"), list):
            merged["prompts"] = []
        if not isinstance(merged.get("settings"), dict):
            merged["settings"] = {}

        # Apply base settings but don't override what LLM might have provided unless missing
        base_settings = self._base_settings(ctx)
        for k, v in base_settings.items():
            merged["settings"].setdefault(k, v)

        # Shape enforcement
        spec = self._format_spec(fmt)
        shape = str(spec.get("shape") or "").strip()

        # Default body/items to safe values
        if shape == "body":
            body = merged.get("body")
            if not isinstance(body, str) or not body.strip():
                merged["body"] = "not specified"
            merged["items"] = []  # must be empty for body formats
        else:
            merged["body"] = None  # items formats: body must be null
            if not isinstance(merged.get("items"), list):
                merged["items"] = []

        # If scripts: ensure target_duration_sec is set
        if fmt in {"script_short", "script_long"}:
            merged["settings"].setdefault("target_duration_sec", 30 if fmt == "script_short" else 120)

        # Normalize items structure with minimal safety (don't over-police)
        merged["items"] = self._normalize_items(fmt=fmt, items=merged.get("items") or [])

        # Keep payload free from redundant metadata fields.
        merged.pop("keywords", None)
        merged.pop("tags_json", None)

        return merged

    @staticmethod
    def _normalize_items(fmt: str, items: list[Any]) -> list[dict[str, Any]]:
        """
        Minimal item normalization to keep downstream consumers stable.
        """
        normalized: list[dict[str, Any]] = []

        # Map fmt -> expected item_type (when applicable)
        expected_item_type: str | None = None
        if fmt == "x_thread":
            expected_item_type = "tweet"
        elif fmt in {"script_short", "script_long"}:
            expected_item_type = "beat"
        elif fmt == "hook_bank":
            expected_item_type = "hook"
        elif fmt == "headline_variants":
            expected_item_type = "headline"
        elif fmt == "cta_variants":
            expected_item_type = "cta"
        elif fmt == "faq":
            expected_item_type = "qa"
        elif fmt == "playbook":
            expected_item_type = "step"

        seq = 1
        for it in items:
            if not isinstance(it, dict):
                continue
            item_type = str(it.get("item_type") or expected_item_type or "item").strip()
            if expected_item_type and item_type != expected_item_type:
                # Keep the expected type consistent for downstream rendering
                item_type = expected_item_type

            row: dict[str, Any] = {"item_type": item_type, "sequence": PlanTextStage._safe_int(it.get("sequence"), seq)}
            # Common fields: ensure text always exists for item-based formats.
            row["text"] = str(it.get("text") or "").strip() or "not specified"
            # FAQ/playbook need title
            if expected_item_type in {"qa", "step"}:
                row["title"] = str(it.get("title") or "").strip() or "not specified"
                row["text"] = str(it.get("text") or "").strip() or "not specified"

            normalized.append(row)
            seq += 1

        # Ensure at least one item for item-based formats
        if expected_item_type and not normalized:
            if expected_item_type == "qa":
                normalized = [{"item_type": "qa", "sequence": 1, "title": "not specified", "text": "not specified"}]
            elif expected_item_type == "step":
                normalized = [{"item_type": "step", "sequence": 1, "title": "not specified", "text": "not specified"}]
            else:
                normalized = [{"item_type": expected_item_type, "sequence": 1, "text": "not specified"}]

        return normalized

    def _normalize_tags(self, *, llm_tags: Any, ctx: PipelineContext) -> list[str]:
        """
        tags_json: deduped tags built from LLM tags + seed keywords.
        """
        tags: list[str] = []
        if isinstance(llm_tags, list):
            tags = [str(x).strip() for x in llm_tags if str(x).strip()]
        merged = self._dedupe_keep_order(list(ctx.seed_keywords or []) + tags)
        merged = [x for x in merged if x.lower() != "not specified"]
        if not merged:
            merged = [x for x in self._dedupe_keep_order(list(ctx.seed_keywords or [])) if x.lower() != "not specified"]
        return merged[:20]

    # -----------------------------
    # LLM generation (improved prompt)
    # -----------------------------
    def _generate_with_llm(self, *, fmt: str, ctx: PipelineContext) -> dict[str, Any]:
        if not (self.enable_llm and self.llm and self.llm.enabled):
            return {}

        spec = self._format_spec(fmt)

        system_prompt = """
You generate ONE text artifact for a content pipeline.

Non-negotiables:
- Output MUST be a single JSON object. No markdown. No commentary.
- Top-level keys allowed ONLY: title, payload_json, tags_json.
- Grounding: Use ONLY provided core_idea + master_body + seed_keywords. Do NOT add new factual claims.
- If missing information, write "not specified" (do not guess).
""".strip()

        # Keep prompt compact but explicit about the required shape.
        # We do NOT ask the model to do style_settings merging; we do that server-side.
        user_prompt = f"""
FORMAT={fmt}
FORMAT_SPEC={json.dumps(spec, ensure_ascii=False)}

INPUTS:
- topic_title: {ctx.topic_title or "not specified"}
- core_idea (keep meaning unchanged): {ctx.core_idea or "not specified"}
- master_body: {((ctx.master_body or "not specified").strip())[:6000]}
- seed_keywords: {json.dumps(list(ctx.seed_keywords or []), ensure_ascii=False)}
- target_audience: {ctx.target_audience or "not specified"}
- content_depth: {ctx.content_depth or "not specified"}
- tone_preference: {ctx.tone_preference or "not specified"}

ENVELOPE (must match):
{{
  "version": "1.0",
  "body": null,
  "items": [],
  "assets": [],
  "prompts": [],
  "settings": {{}},
  "notes": null
}}

SHAPE RULES:
- If FORMAT_SPEC.shape == "body":
  - payload_json.body MUST be a STRING (final text).
  - payload_json.items MUST be [].
- If FORMAT_SPEC.shape starts with "items(":
  - payload_json.body MUST be null.
  - payload_json.items MUST contain objects with:
    - item_type: based on the format (tweet/beat/hook/headline/cta/qa/step)
    - sequence: 1..N
    - text: string
    - If qa/step: also include title.

TAGS:
- tags_json MUST include 8–20 concise tags derived from generated content and seed_keywords (dedupe). No hashtags.

Return STRICT JSON only:
{{
  "title": "<string>",
  "payload_json": {{ ... }},
  "tags_json": ["<string>", "..."]
}}
""".strip()

        raw = self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2, max_tokens=1800)
        return parse_json_object(raw) or {}

    def _repair_with_llm(self, *, fmt: str, ctx: PipelineContext, bad_json: str) -> dict[str, Any]:
        """
        One-shot repair prompt if the first call returns invalid JSON or wrong shape.
        Keeps tokens small and improves reliability.
        """
        if not (self.enable_llm and self.llm and self.llm.enabled):
            return {}

        spec = self._format_spec(fmt)
        system_prompt = """
You fix a broken JSON response for a content pipeline.

Rules:
- Return STRICT JSON only (single object).
- Top-level keys allowed ONLY: title, payload_json, tags_json.
- Do not add new facts beyond the provided master_body.
""".strip()

        user_prompt = f"""
FORMAT={fmt}
FORMAT_SPEC={json.dumps(spec, ensure_ascii=False)}

MASTER_BODY (facts source):
{((ctx.master_body or "not specified").strip())[:6000]}

BROKEN_OUTPUT:
{bad_json[:6000]}

Fix it to match the required schema and shape rules. Return ONLY the corrected JSON object.
""".strip()

        raw = self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.0, max_tokens=1200)
        return parse_json_object(raw) or {}

    # -----------------------------
    # Stage runner
    # -----------------------------
    def run(self, ctx: PipelineContext) -> StageResult:
        formats = [f for f in (ctx.requested_formats or []) if f in TEXT_FORMATS]
        drafts: list[ArtifactDraft] = []

        for fmt in formats:
            fallback_payload = self._fallback_payload(fmt=fmt, ctx=ctx)

            llm_out: dict[str, Any] = {}
            try:
                # First attempt
                llm_out = self._generate_with_llm(fmt=fmt, ctx=ctx)
            except Exception as e:
                llm_out = {}
                raw_attempt = str(e)
                repaired = self._repair_with_llm(fmt=fmt, ctx=ctx, bad_json=raw_attempt)
                if isinstance(repaired, dict) and repaired:
                    llm_out = repaired

            # If output is still empty/malformed, use deterministic fallback.
            if not isinstance(llm_out, dict) or not llm_out:
                llm_out = {}

            raw_payload = llm_out.get("payload_json") if isinstance(llm_out, dict) else None
            if not isinstance(raw_payload, dict):
                payload = fallback_payload
            else:
                payload = self._merge_and_normalize_payload(raw_payload=raw_payload, fmt=fmt, ctx=ctx)

            # Title
            title = (
                str((llm_out.get("title") if isinstance(llm_out, dict) else "") or "").strip()
                or f"{(ctx.topic_title or 'AI Topic').strip()} - {fmt.replace('_', ' ').title()}"
            )

            # Tags
            tags = self._normalize_tags(llm_tags=(llm_out.get("tags_json") if isinstance(llm_out, dict) else None), ctx=ctx)

            drafts.append(
                ArtifactDraft(
                    format=fmt,
                    title=title,
                    payload_json=payload,
                    tags_json=tags,
                )
            )

        return StageResult(stage=self.name, drafts=drafts)
