from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol

from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext


class ArtifactFormatBuilder(Protocol):
    kind: str
    formats: set[str]

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        ...

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
        ...


@dataclass(frozen=True)
class RegisteredBuilder:
    module_name: str
    builder: ArtifactFormatBuilder
