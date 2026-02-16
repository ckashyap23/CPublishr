from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.contracts.prd import ContentDepth, DistributionTarget, TargetAudience, TonePreference


class ContextBundleV1(BaseModel):
    """
    Canonical shape of the project context bundle produced by Node 0.

    We allow extra keys because later stages (e.g., Node 2 / adapters) may
    enrich this object with additional derived fields.
    """

    model_config = ConfigDict(extra="allow")

    topic_title: str
    normalized_topic: str
    core_idea: str
    user_content: str | None = None
    target_audience: TargetAudience | None = None
    content_depth: ContentDepth | None = None
    tone_preference: TonePreference
    distribution_targets: list[DistributionTarget]


