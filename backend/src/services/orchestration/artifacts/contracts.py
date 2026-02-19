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
    project_id: str
    topic_title: str
    core_idea: str
    master_body: str
    seed_keywords: list[str]
    target_audience: str | None = None
    content_depth: str | None = None
    tone_preference: str | None = None
    requested_formats: list[str] = field(default_factory=list)
    style_settings: dict[str, Any] = field(default_factory=dict)
    stage_outputs: dict[str, list[ArtifactDraft]] = field(default_factory=dict)


@dataclass
class StageResult:
    stage: str
    drafts: list[ArtifactDraft]


@dataclass
class GenerationOptions:
    run_plan: bool = True
    run_prompt_pack: bool = True
    run_render_media: bool = True
    run_assemble: bool = True
    run_package: bool = True
    revision_mode: str = "new_revision"  # new_revision | reset
