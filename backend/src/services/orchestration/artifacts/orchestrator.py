from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from sqlalchemy.orm import Session

from src.db.repositories.artifact_repository import ArtifactRepository
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.services.orchestration.artifact_schema import allowed_formats, normalize_payload, validate_payload_shape
from src.services.orchestration.artifacts.contracts import ArtifactDraft, GenerationOptions, PipelineContext
from src.services.orchestration.artifacts.formats.registry import get_kind_by_format, resolve_builder
from src.utils.ids import new_id


class ArtifactPipelineOrchestrator:
    """Per-format artifact generation pipeline (no stage fan-out)."""

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.projects = ProjectRepository(db, user_id=user_id)
        self.contents = ContentRepository(db, user_id=user_id)
        self.artifacts = ArtifactRepository(db, user_id=user_id)

    @staticmethod
    def _normalize_image_kind_settings(style_settings: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(style_settings, dict):
            return {}

        out: dict[str, Any] = {}

        def clean_text(key: str, max_len: int = 5000) -> None:
            raw = style_settings.get(key)
            if raw is None:
                return
            value = str(raw).strip()
            if value:
                out[key] = value[:max_len]

        def clean_enum(key: str, allowed: set[str]) -> None:
            raw = style_settings.get(key)
            if raw is None:
                return
            value = str(raw).strip().lower()
            if value in allowed:
                out[key] = value

        clean_text("theme", 240)
        clean_text("subject_prompt", 4000)

        raw_avoid = style_settings.get("avoid")
        if isinstance(raw_avoid, list):
            avoid_out: list[str] = []
            seen: set[str] = set()
            for item in raw_avoid:
                tag = str(item or "").strip()
                if not tag:
                    continue
                key = tag.lower()
                if key in seen:
                    continue
                seen.add(key)
                avoid_out.append(tag[:80])
            if avoid_out:
                out["avoid"] = avoid_out

        clean_enum(
            "medium",
            {"photo", "illustration", "3d_render", "comic", "watercolor", "oil_paint", "vector_flat", "pixel_art"},
        )
        clean_enum("texture", {"clean", "film_grain", "halftone", "paper", "canvas", "noise"})
        clean_enum(
            "palette_mode",
            {"brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"},
        )
        clean_enum("mood", {"playful", "serious", "premium", "cozy", "dramatic", "energetic"})
        clean_enum(
            "focus_negative_space",
            {"subject_centered", "rule_of_thirds", "negative_space_left", "negative_space_right"},
        )

        # UI may send output_fidelity as "Standard"/"HD"; normalize to connector quality values.
        raw_fidelity = style_settings.get("output_fidelity")
        if raw_fidelity is not None:
            fidelity = str(raw_fidelity).strip().lower()
            if fidelity in {"hd", "standard"}:
                out["output_fidelity"] = fidelity
            elif fidelity in {"true", "1"}:
                out["output_fidelity"] = "hd"
            elif fidelity in {"false", "0"}:
                out["output_fidelity"] = "standard"

        raw_brand_colors = style_settings.get("brand_colors")
        if isinstance(raw_brand_colors, dict):
            colors: dict[str, str] = {}
            for key in ("primary", "secondary", "accent", "background"):
                raw = raw_brand_colors.get(key)
                if raw is None:
                    continue
                color = str(raw).strip()
                if color and len(color) <= 16:
                    colors[key] = color
            if colors:
                out["brand_colors"] = colors

        return out

    @staticmethod
    def _merge_tags(seed_keywords: list[str], payload: dict[str, Any], existing: list[str] | None = None) -> list[str]:
        acc: list[str] = []
        for source in [seed_keywords, payload.get("keywords") or [], existing or []]:
            for item in source:
                s = str(item).strip()
                if s and s not in acc:
                    acc.append(s)
        return acc

    @staticmethod
    def _style_settings_for_format(
        fmt: str,
        *,
        shared: dict[str, Any] | None = None,
        by_kind: dict[str, dict[str, Any]] | None = None,
        by_format: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        _ = shared  # legacy shared style_settings are intentionally ignored; use by_kind + by_format
        merged: dict[str, Any] = {}
        if isinstance(by_kind, dict):
            kind = get_kind_by_format().get(fmt)
            if kind:
                kind_settings = by_kind.get(kind)
                if isinstance(kind_settings, dict):
                    merged.update(kind_settings)
        if isinstance(by_format, dict):
            fmt_settings = by_format.get(fmt)
            if isinstance(fmt_settings, dict):
                merged.update(fmt_settings)
        return merged

    @staticmethod
    def _normalize_style_source(style_settings: dict[str, Any] | None) -> str | None:
        if not isinstance(style_settings, dict):
            return None
        src = str(style_settings.get("style_source") or "").strip().lower()
        return src if src in {"manual", "voice_profile"} else None

    @staticmethod
    def _normalize_voice_profile_id(
        *,
        bundle: dict[str, Any] | None = None,
        style_settings: dict[str, Any] | None = None,
    ) -> str | None:
        shared = style_settings or {}
        candidate = str(shared.get("voice_profile_id") or "").strip()
        if candidate:
            return candidate
        if isinstance(bundle, dict):
            candidate = str(bundle.get("voice_profile_id") or "").strip()
            if candidate:
                return candidate
        return None

    @staticmethod
    def _normalize_tone_base(
        *,
        bundle: dict[str, Any] | None = None,
        style_settings: dict[str, Any] | None = None,
    ) -> str | None:
        # tone_base is derived from project context only (not overridable by artifact UI style settings)
        _ = style_settings  # reserved for signature compatibility
        if isinstance(bundle, dict):
            pref = str(bundle.get("tone_preference") or "").strip().lower()
            if pref in {"analytical", "professional", "conversational"}:
                return pref
        return None

    @staticmethod
    def _normalize_tone_nuance(style_settings: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(style_settings, dict):
            return {}
        raw = style_settings.get("tone_nuance")
        if not isinstance(raw, dict):
            return {}
        return dict(raw)

    @staticmethod
    def _normalize_style_context(style_settings: dict[str, Any] | None) -> dict[str, Any]:
        """
        Normalize UI style payload into the shape expected by text_artifacts.py:
        - manual: {core_voice, ...optional}
        - voice_profile: {core_voice, style_summary, do_rules, dont_rules, exemplars, tone_baseline, ...}
        """
        if not isinstance(style_settings, dict):
            return {}

        out: dict[str, Any] = {}
        src = str(style_settings.get("style_source") or "").strip().lower()

        if src == "manual":
            core_voice = style_settings.get("core_voice")
            if isinstance(core_voice, str) and core_voice.strip():
                out["core_voice"] = core_voice.strip()
            return out

        if src != "voice_profile":
            return out

        preview = style_settings.get("voice_profile_preview")
        if isinstance(preview, dict):
            for key in ("core_voice", "style_summary", "tone_baseline", "do_rules", "dont_rules", "exemplars"):
                if key in preview:
                    out[key] = preview.get(key)

        edits = style_settings.get("voice_profile_edits")
        if isinstance(edits, dict):
            # Overlay editable fields on top of preview. Keep explicit arrays/dicts if provided.
            for key in ("core_voice", "style_summary", "do_rules", "dont_rules", "exemplars"):
                if key not in edits:
                    continue
                value = edits.get(key)
                if isinstance(value, str):
                    value = value.strip()
                out[key] = value

        return out

    @staticmethod
    def _normalize_format_overrides(
        style_settings_by_format: dict[str, dict[str, Any]] | None,
    ) -> dict[str, dict[str, Any]]:
        if not isinstance(style_settings_by_format, dict):
            return {}
        out: dict[str, dict[str, Any]] = {}
        for fmt, value in style_settings_by_format.items():
            key = str(fmt or "").strip()
            if not key:
                continue
            if isinstance(value, dict):
                out[key] = dict(value)
        return out

    @staticmethod
    def _normalize_style_settings_by_kind(
        style_settings_by_kind: dict[str, dict[str, Any]] | None,
    ) -> dict[str, dict[str, Any]]:
        if not isinstance(style_settings_by_kind, dict):
            return {}
        out: dict[str, dict[str, Any]] = {}
        for kind, value in style_settings_by_kind.items():
            kind_key = str(kind or "").strip().lower()
            if not kind_key or not isinstance(value, dict):
                continue
            if kind_key == "image":
                out[kind_key] = ArtifactPipelineOrchestrator._normalize_image_kind_settings(value)
            else:
                out[kind_key] = dict(value)
        return out

    def _build_context(
        self,
        *,
        project_id: str,
        requested_formats: list[str],
        style_settings: dict[str, Any] | None = None,
        style_settings_by_kind: dict[str, dict[str, Any]] | None = None,
        style_settings_by_format: dict[str, dict[str, Any]] | None = None,
    ) -> PipelineContext:
        bundle = self.projects.get_context_bundle(project_id) or {}
        final_version = self.contents.get_latest_final_version(project_id)
        source = final_version or self.contents.get_latest_version(project_id)
        master_body = source.content if source else "not specified"
        seed_keywords = self.contents.decode_keywords(source) if source else []
        topic_title = str(bundle.get("topic_title") or "Master Content")
        core_idea = str(bundle.get("core_idea") or "")
        supported = allowed_formats()
        invalid_formats = [f for f in requested_formats if f not in supported]
        if invalid_formats:
            raise ValueError(f"Unsupported format(s): {', '.join(sorted(set(invalid_formats)))}")
        normalized_formats = [f for f in requested_formats if f in supported]

        shared_style_settings = dict(style_settings or {})
        normalized_style_settings_by_kind = self._normalize_style_settings_by_kind(style_settings_by_kind)
        normalized_format_overrides = self._normalize_format_overrides(style_settings_by_format)
        text_style_settings = normalized_style_settings_by_kind.get("text") or {}
        image_style_settings = normalized_style_settings_by_kind.get("image") or {}

        return PipelineContext(
            user_id=self.user_id,
            project_id=project_id,
            context_bundle=bundle,
            topic_title=topic_title,
            core_idea=core_idea,
            master_body=master_body,
            seed_keywords=seed_keywords,
            target_audience=bundle.get("target_audience"),
            audience_familiarity=bundle.get("audience_familiarity"),
            detail_level=bundle.get("detail_level"),
            tone_preference=bundle.get("tone_preference"),
            requested_formats=normalized_formats,
            style_settings=shared_style_settings,
            style_settings_by_kind=normalized_style_settings_by_kind,
            style_settings_by_format=normalized_format_overrides,
            style_source=self._normalize_style_source(text_style_settings),
            voice_profile_id=self._normalize_voice_profile_id(bundle=bundle, style_settings=text_style_settings),
            tone_base=self._normalize_tone_base(bundle=bundle, style_settings=text_style_settings),
            tone_nuance=self._normalize_tone_nuance(text_style_settings),
            style_context=self._normalize_style_context(text_style_settings),
            image_style_settings=image_style_settings,
            format_overrides=normalized_format_overrides,
        )

    def _persist_draft(self, *, project_id: str, draft: ArtifactDraft, revision_mode: str) -> dict[str, Any]:
        payload = normalize_payload(draft.payload_json)
        validate_payload_shape(draft.format, payload)
        tags = self._merge_tags([], payload, draft.tags_json)

        if revision_mode == "reset":
            row = self.artifacts.create_artifact(
                artifact_id=new_id("art"),
                project_id=project_id,
                format=draft.format,
                title=draft.title,
                payload_json=payload,
                tags_json=tags,
                status=draft.status,
                revision=max(1, int(draft.revision or 1)),
                parent_artifact_id=draft.parent_artifact_id,
            )
        else:
            row = self.artifacts.create_next_revision(
                artifact_id=new_id("art"),
                project_id=project_id,
                format=draft.format,
                title=draft.title,
                payload_json=payload,
                tags_json=tags,
                status=draft.status,
            )

        return {
            "artifact_id": row.artifact_id,
            "project_id": row.project_id,
            "format": row.format,
            "kind": row.kind,
            "title": row.title,
            "payload_json": row.payload_json or {},
            "tags_json": row.tags_json or [],
            "status": row.status,
            "revision": row.revision,
            "parent_artifact_id": row.parent_artifact_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def generate(
        self,
        *,
        project_id: str,
        requested_formats: list[str],
        options: GenerationOptions | None = None,
        style_settings: dict[str, Any] | None = None,
        style_settings_by_kind: dict[str, dict[str, Any]] | None = None,
        style_settings_by_format: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        opts = options or GenerationOptions()
        self.projects.get_or_create(project_id)
        ctx = self._build_context(
            project_id=project_id,
            requested_formats=requested_formats,
            style_settings=style_settings,
            style_settings_by_kind=style_settings_by_kind,
            style_settings_by_format=style_settings_by_format,
        )

        if opts.revision_mode == "reset":
            self.artifacts.delete_artifacts_for_project(project_id)

        persisted: list[dict[str, Any]] = []
        for fmt in ctx.requested_formats:
            builder = resolve_builder(fmt)
            if builder is None:
                raise ValueError(f"No format builder registered for: {fmt}")
            fmt_ctx = replace(
                ctx,
                style_settings=self._style_settings_for_format(
                    fmt,
                    shared=style_settings,
                    by_kind=style_settings_by_kind,
                    by_format=style_settings_by_format,
                ),
            )
            draft = builder.build(fmt=fmt, ctx=fmt_ctx)
            if str(getattr(builder, "kind", "")).strip() == "image" and str(draft.status or "").strip().lower() != "generated":
                # Do not persist failed/simulated image artifacts.
                continue
            persisted.append(self._persist_draft(project_id=project_id, draft=draft, revision_mode=opts.revision_mode))

        return {
            "project_id": project_id,
            "requested_formats": list(requested_formats),
            "options": asdict(opts),
            "artifacts": persisted,
        }
