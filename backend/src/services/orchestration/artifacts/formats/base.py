from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext


class ArtifactFormatBuilder(Protocol):
    kind: str
    formats: set[str]

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        ...


@dataclass(frozen=True)
class RegisteredBuilder:
    module_name: str
    builder: ArtifactFormatBuilder

