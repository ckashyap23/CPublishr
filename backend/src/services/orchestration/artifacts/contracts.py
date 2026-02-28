from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArtifactDraft:
    format: str
    title: str | None
    payload_json: dict[str, Any]
    tags_json: list[str] = field(default_factory=list)
    status: str = "generated"
    revision: int = 1
    parent_artifact_id: str | None = None


@dataclass
class PipelineContext:
    user_id: str
    project_id: str
    context_bundle: dict[str, Any]
    topic_title: str
    core_idea: str
    master_body: str
    seed_keywords: list[str]
    target_audience: dict[str, Any] | None = None
    audience_familiarity: str | None = None
    detail_level: str | None = None
    tone_preference: str | None = None
    requested_formats: list[str] = field(default_factory=list)
    style_settings: dict[str, Any] = field(default_factory=dict)
    style_settings_by_kind: dict[str, dict[str, Any]] = field(default_factory=dict)
    style_settings_by_format: dict[str, dict[str, Any]] = field(default_factory=dict)
    style_source: str | None = None
    voice_profile_id: str | None = None
    tone_base: str | None = None
    tone_nuance: dict[str, Any] = field(default_factory=dict)
    style_context: dict[str, Any] = field(default_factory=dict)
    image_style_settings: dict[str, Any] = field(default_factory=dict)
    video_style_settings: dict[str, Any] = field(default_factory=dict)
    format_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class StageResult:
    stage: str
    drafts: list[ArtifactDraft]


@dataclass
class GenerationOptions:
    revision_mode: str = "new_revision"  # new_revision | reset
