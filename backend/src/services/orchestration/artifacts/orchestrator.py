from __future__ import annotations

import json
import re
from dataclasses import asdict, replace
from typing import Any

from sqlalchemy.orm import Session

from src.db.repositories.artifact_repository import ArtifactRepository
from src.db.repositories.content_repository import ContentRepository
from src.db.repositories.project_repository import ProjectRepository
from src.services.orchestration.artifact_schema import allowed_formats, normalize_payload, validate_payload_shape
from src.services.orchestration.artifacts.contracts import ArtifactDraft, GenerationOptions, PipelineContext
from src.services.orchestration.artifacts.formats.registry import get_kind_by_format, resolve_builder
from src.services.storage.artifact_blob_storage import overwrite_blob_text
from src.services.storage.prompt_blob_storage import save_prompt_text
from src.utils.ids import new_id


class ArtifactPipelineOrchestrator:
    """Per-format artifact generation pipeline (no stage fan-out)."""
    QC_PROMPT_SUFFIXES = {
        "build": "build_prompt",
        "edit_inline": "edit_inline",
        "edit_original": "original_prompt",
        "edit_instruction": "edit_instruction",
        "edit_effective": "edit_prompt",
    }

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
    def _normalize_video_kind_settings(style_settings: dict[str, Any] | None) -> dict[str, Any]:
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
            "mood",
            {
                "playful",
                "serious",
                "premium",
                "cozy",
                "dramatic",
                "energetic",
                "inspiring",
                "suspenseful",
                "mysterious",
                "whimsical",
                "futuristic",
                "nostalgic",
            },
        )
        clean_enum(
            "lighting",
            {
                "soft_daylight",
                "golden_hour",
                "sunset_warm",
                "overcast_diffused",
                "studio_softbox",
                "high_key_bright",
                "low_key_moody",
                "neon_night",
                "backlit_silhouette",
                "rim_light",
                "volumetric_godrays",
                "dramatic_spotlight",
            },
        )
        clean_enum(
            "palette_mode",
            {"brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"},
        )
        clean_enum("output_fidelity", {"standard", "pro"})

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
    def _extract_prompt_text(payload: dict[str, Any], *, preferred_names: list[str] | None = None) -> str:
        prompts = payload.get("prompts") if isinstance(payload.get("prompts"), list) else []
        names = [str(x).strip().lower() for x in (preferred_names or []) if str(x).strip()]
        if names:
            for item in prompts:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip().lower()
                text = str(item.get("text") or "").strip()
                if name in names and text:
                    return text
        for item in prompts:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text:
                return text
        return ""

    def _save_qc_format_prompt(
        self,
        *,
        project_id: str,
        kind: str,
        name: str,
        suffix: str,
        text: str,
        subfolder: str | None = None,
    ) -> dict[str, str] | None:
        if not str(text or "").strip():
            return None
        resolved_subfolder = str(subfolder or "").strip() or str(kind or "artifact")
        return save_prompt_text(
            user_id=self.user_id,
            project_id=project_id,
            section="qc-formats",
            subfolder=resolved_subfolder,
            name=str(name or "artifact"),
            suffix=str(suffix or "prompt"),
            text=str(text),
        )

    @staticmethod
    def _qc_prompt_name_for_build(*, fmt: str, artifact_id: str | None, title: str | None) -> str:
        safe_fmt = str(fmt or "artifact").strip() or "artifact"
        safe_id = str(artifact_id or "").strip() or "na"
        safe_title = str(title or "").strip() or "artifact"
        return f"{safe_fmt}_{safe_id}_{safe_title}"

    @staticmethod
    def _qc_prompt_name_for_edit(source: Any) -> str:
        safe_fmt = str(getattr(source, "format", "") or "").strip() or "artifact"
        safe_id = str(getattr(source, "artifact_id", "") or "").strip() or "na"
        safe_title = str(getattr(source, "title", "") or "").strip() or "artifact"
        return f"{safe_fmt}_{safe_id}_{safe_title}"

    def _save_build_prompts_for_draft(
        self,
        *,
        project_id: str,
        fmt: str,
        draft: ArtifactDraft,
        artifact_id: str | None,
        title: str | None,
    ) -> dict[str, str] | None:
        payload = draft.payload_json if isinstance(draft.payload_json, dict) else {}
        prompt_text = self._extract_prompt_text(
            payload,
            preferred_names=["artifact_prompt", "iterate_prompt", "image_prompt", "video_prompt"],
        )
        kind = str(get_kind_by_format().get(fmt) or "artifact")
        ref = self._save_qc_format_prompt(
            project_id=project_id,
            kind=kind,
            name=self._qc_prompt_name_for_build(fmt=fmt, artifact_id=artifact_id, title=title),
            suffix=self.QC_PROMPT_SUFFIXES["build"],
            text=prompt_text,
        )
        if not ref:
            return None

        settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
        settings["qc_prompt_blob_path"] = ref.get("blob_path")
        settings["qc_prompt_uri"] = ref.get("uri")
        payload["settings"] = settings

        prompts = payload.get("prompts") if isinstance(payload.get("prompts"), list) else []
        preferred_names = {"artifact_prompt", "iterate_prompt", "image_prompt", "video_prompt"}
        attached = False
        for item in prompts:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip().lower()
            text = str(item.get("text") or "").strip()
            if name in preferred_names and text:
                item["blob_path"] = ref.get("blob_path")
                item["uri"] = ref.get("uri")
                attached = True
                break
        if not attached and prompt_text:
            prompts.append(
                {
                    "name": "qc_prompt",
                    "text": prompt_text,
                    "tool": "azure_blob",
                    "blob_path": ref.get("blob_path"),
                    "uri": ref.get("uri"),
                }
            )
        payload["prompts"] = prompts
        draft.payload_json = payload
        return ref

    @staticmethod
    def _qc_iteration_subfolder(*, kind: str, qc_name: str, iteration_number: int) -> str:
        safe_kind = str(kind or "artifact").strip() or "artifact"
        safe_name = str(qc_name or "artifact").strip() or "artifact"
        safe_iteration = max(1, int(iteration_number or 1))
        return f"{safe_kind}/{safe_name}_iterations/v{safe_iteration}"

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
            elif kind_key in {"video", "gif"}:
                out[kind_key] = ArtifactPipelineOrchestrator._normalize_video_kind_settings(value)
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
        video_style_settings = normalized_style_settings_by_kind.get("video") or {}

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
            video_style_settings=video_style_settings,
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

    @staticmethod
    def _inline_content_to_payload(*, fmt: str, payload: dict[str, Any], inline_content: str) -> dict[str, Any]:
        out = normalize_payload(payload)
        text = str(inline_content or "")
        if fmt == "script_short":
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            out["body"] = None
            out["items"] = [
                {"item_type": "beat", "sequence": i + 1, "text": ln}
                for i, ln in enumerate(lines)
            ]
            return out
        if fmt == "cta_variants":
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            out["body"] = None
            out["items"] = [
                {"item_type": "cta", "sequence": i + 1, "text": ln}
                for i, ln in enumerate(lines)
            ]
            return out
        out["body"] = text
        return out

    @staticmethod
    def _find_first_text_blob_asset(payload: dict[str, Any]) -> dict[str, Any] | None:
        assets = payload.get("assets")
        if not isinstance(assets, list):
            return None
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            blob_path = str(asset.get("blob_path") or "").strip()
            if not blob_path:
                continue
            mime = str(asset.get("mime_type") or "").strip().lower()
            fmt = str(asset.get("format") or "").strip().lower()
            if mime.startswith("text/") or "json" in mime or fmt in {"txt", "json"}:
                return asset
        return None

    @staticmethod
    def _extract_text_for_blob(*, fmt: str, payload: dict[str, Any]) -> tuple[str, str]:
        if fmt == "script_short" or fmt == "cta_variants":
            return (json.dumps(payload, ensure_ascii=False, indent=2), "application/json")
        body = payload.get("body")
        return (str(body) if body is not None else "", "text/plain; charset=utf-8")

    @staticmethod
    def _split_title_version(title: str | None) -> tuple[str, int | None]:
        raw = str(title or "").strip()
        if not raw:
            return ("Artifact", None)
        m = re.match(r"^(.*?)\s+v(\d+)$", raw, flags=re.IGNORECASE)
        if not m:
            return (raw, None)
        base = str(m.group(1) or "").strip() or "Artifact"
        try:
            version = int(m.group(2))
        except Exception:
            version = None
        return (base, version)

    @classmethod
    def _next_iterated_title_and_version(cls, source_title: str | None, siblings: list[Any]) -> tuple[str, int]:
        base, source_version = cls._split_title_version(source_title)
        pattern = re.compile(rf"^{re.escape(base)}\s+v(\d+)$", re.IGNORECASE)
        max_v = max(1, int(source_version or 1))
        for row in siblings:
            title = str(getattr(row, "title", "") or "").strip()
            if not title:
                continue
            if title.lower() == base.lower():
                max_v = max(max_v, 1)
                continue
            m = pattern.match(title)
            if not m:
                continue
            try:
                max_v = max(max_v, int(m.group(1)))
            except Exception:
                continue
        next_v = max_v + 1
        return (f"{base} v{next_v}", next_v)

    def _resolve_source_artifacts_from_blob_paths(self, *, project_id: str, blob_paths: list[str]) -> list[dict[str, Any]]:
        rows = self.artifacts.find_artifacts_by_blob_paths(project_id=project_id, blob_paths=blob_paths)
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            key = str(getattr(row, "artifact_id", "") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(self._to_entity_dict(row))
        return out

    def _to_entity_dict(self, row) -> dict[str, Any]:
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

    def edit_artifact(
        self,
        *,
        artifact_id: str,
        mode: str,
        inline_content: str | None = None,
        edit_instruction: str | None = None,
        style_settings_by_kind: dict[str, dict[str, Any]] | None = None,
        style_settings_by_format: dict[str, dict[str, Any]] | None = None,
        source_blob_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        source = self.artifacts.get_artifact(artifact_id)
        if source is None:
            raise ValueError("Artifact not found")

        edit_mode = str(mode or "").strip().lower()
        if edit_mode not in {"inline", "iterate"}:
            raise ValueError("mode must be 'inline' or 'iterate'")

        if edit_mode == "inline":
            if str(source.kind or "").strip().lower() != "text":
                raise ValueError("Inline edit is only supported for text artifacts")
            next_text = str(inline_content or "")
            self._save_qc_format_prompt(
                project_id=source.project_id,
                kind=str(source.kind or "text"),
                name=self._qc_prompt_name_for_edit(source),
                suffix=self.QC_PROMPT_SUFFIXES["edit_inline"],
                text=next_text,
            )
            payload = self._inline_content_to_payload(
                fmt=str(source.format or ""),
                payload=(source.payload_json or {}),
                inline_content=next_text,
            )

            # Overwrite original text blob (same blob path + same artifact id lineage).
            text_blob_asset = self._find_first_text_blob_asset(payload)
            if text_blob_asset:
                blob_path = str(text_blob_asset.get("blob_path") or "").strip()
                if blob_path:
                    blob_text, blob_content_type = self._extract_text_for_blob(fmt=str(source.format or ""), payload=payload)
                    blob_ref = overwrite_blob_text(blob_path=blob_path, text=blob_text, content_type=blob_content_type)
                    if blob_ref and blob_ref.get("uri"):
                        text_blob_asset["uri"] = blob_ref["uri"]

            updated = self.artifacts.update_artifact(
                artifact_id,
                payload_json=payload,
                status="edited_inline",
            )
            if updated is None:
                raise ValueError("Failed to update artifact")
            return {"status": "edited_inline", "artifact": self._to_entity_dict(updated)}

        # Iterate mode: pass-through plumbing for format builders to implement edit() later.
        builder = resolve_builder(str(source.format or ""))
        if builder is None:
            raise ValueError(f"No format builder registered for format '{source.format}'")

        edit_fn = getattr(builder, "edit", None)
        if not callable(edit_fn):
            raise ValueError(
                f"Iterate edit is not implemented for format '{source.format}'. "
                "Add `edit(fmt, ctx, source_artifact, edit_instruction, target_artifact_id, source_blob_paths)` in the builder."
            )

        style_by_kind = style_settings_by_kind or {}
        style_by_format = style_settings_by_format or {}
        ctx = self._build_context(
            project_id=source.project_id,
            requested_formats=[str(source.format or "")],
            style_settings_by_kind=style_by_kind,
            style_settings_by_format=style_by_format,
        )
        fmt = str(source.format or "")
        fmt_ctx = replace(
            ctx,
            style_settings=self._style_settings_for_format(
                fmt,
                by_kind=style_by_kind,
                by_format=style_by_format,
            ),
        )

        source_artifact_dict = self._to_entity_dict(source)
        source_payload = source_artifact_dict.get("payload_json") if isinstance(source_artifact_dict.get("payload_json"), dict) else {}
        source_prompts = source_payload.get("prompts") if isinstance(source_payload.get("prompts"), list) else []
        original_prompt_text = ""
        for p in source_prompts:
            if not isinstance(p, dict):
                continue
            candidate = str(p.get("text") or "").strip()
            if candidate:
                original_prompt_text = candidate
                break
        iterate_text = str(edit_instruction or "").strip()
        resolved_blob_paths = [str(x).strip() for x in (source_blob_paths or []) if str(x).strip()]
        source_artifacts_by_blob = self._resolve_source_artifacts_from_blob_paths(
            project_id=source.project_id,
            blob_paths=resolved_blob_paths,
        )

        qc_name = self._qc_prompt_name_for_edit(source)
        iteration_number = max(1, int(source.revision or 1))
        iteration_subfolder = self._qc_iteration_subfolder(
            kind=str(source.kind or "artifact"),
            qc_name=qc_name,
            iteration_number=iteration_number,
        )

        new_artifact_id = new_id("art")
        draft = edit_fn(
            fmt=fmt,
            ctx=fmt_ctx,
            source_artifact=source_artifact_dict,
            edit_instruction=iterate_text,
            target_artifact_id=new_artifact_id,
            source_blob_paths=resolved_blob_paths,
        )
        if not isinstance(draft, ArtifactDraft):
            raise ValueError("Builder edit() must return ArtifactDraft")
        draft_payload = draft.payload_json if isinstance(draft.payload_json, dict) else {}
        iterated_prompt_text = self._extract_prompt_text(
            draft_payload,
            preferred_names=["iterate_prompt", "image_prompt", "video_prompt", "artifact_prompt"],
        )
        self._save_qc_format_prompt(
            project_id=source.project_id,
            kind=str(source.kind or "artifact"),
            name=qc_name,
            suffix=self.QC_PROMPT_SUFFIXES["edit_effective"],
            text=iterated_prompt_text,
            subfolder=iteration_subfolder,
        )
        self._save_qc_format_prompt(
            project_id=source.project_id,
            kind=str(source.kind or "artifact"),
            name=qc_name,
            suffix=self.QC_PROMPT_SUFFIXES["edit_original"],
            text=original_prompt_text or "not available",
            subfolder=iteration_subfolder,
        )
        self._save_qc_format_prompt(
            project_id=source.project_id,
            kind=str(source.kind or "artifact"),
            name=qc_name,
            suffix=self.QC_PROMPT_SUFFIXES["edit_instruction"],
            text=iterate_text,
            subfolder=iteration_subfolder,
        )

        siblings = self.artifacts.list_artifacts_by_format(source.project_id, fmt)
        fallback_title = str(source.title or "").strip() or str(draft.title or "").strip() or "Artifact"
        next_title, next_version = self._next_iterated_title_and_version(fallback_title, siblings)
        next_revision = max([int(getattr(row, "revision", 0) or 0) for row in siblings] + [0]) + 1
        payload = normalize_payload(draft.payload_json)
        settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
        settings["iteration_version"] = next_version
        settings["source_blob_paths"] = resolved_blob_paths
        settings["source_artifact_ids_by_blob_path"] = [
            str(x.get("artifact_id") or "").strip()
            for x in source_artifacts_by_blob
            if str(x.get("artifact_id") or "").strip()
        ]
        payload["settings"] = settings
        tags = self._merge_tags([], payload, draft.tags_json)
        row = self.artifacts.create_artifact(
            artifact_id=new_artifact_id,
            project_id=source.project_id,
            format=fmt,
            title=next_title,
            payload_json=payload,
            tags_json=tags,
            status=str(draft.status or "generated"),
            revision=next_revision,
            parent_artifact_id=source.artifact_id,
        )
        return {"status": "iterated", "artifact": self._to_entity_dict(row)}

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
        generation_errors: list[dict[str, Any]] = []
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
            builder_kind = str(getattr(builder, "kind", "")).strip()
            draft_status = str(draft.status or "").strip().lower()
            if builder_kind in {"image", "video", "gif"} and draft_status != "generated":
                # Do not persist failed/partial/simulated media artifacts — but surface the error.
                settings = draft.payload_json.get("settings") if isinstance(draft.payload_json, dict) else {}
                error_msg = str((settings or {}).get("error_message") or "").strip() or f"{fmt} generation {draft_status}."
                generation_errors.append({"format": fmt, "status": draft_status, "error": error_msg})
                continue
            saved = self._persist_draft(project_id=project_id, draft=draft, revision_mode=opts.revision_mode)
            persisted.append(saved)
            prompt_ref = self._save_build_prompts_for_draft(
                project_id=project_id,
                fmt=fmt,
                draft=draft,
                artifact_id=str(saved.get("artifact_id") or ""),
                title=str(saved.get("title") or ""),
            )
            if prompt_ref:
                updated = self.artifacts.update_artifact(
                    str(saved.get("artifact_id") or ""),
                    payload_json=draft.payload_json,
                    status=draft.status,
                )
                if updated is not None:
                    saved["payload_json"] = updated.payload_json or {}

        result: dict[str, Any] = {
            "project_id": project_id,
            "requested_formats": list(requested_formats),
            "options": asdict(opts),
            "artifacts": persisted,
        }
        if generation_errors:
            result["generation_errors"] = generation_errors
        return result
