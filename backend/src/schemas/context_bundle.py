from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.contracts.prd import (
    DetailLevel,
    DesiredAction,
    DistributionTarget,
    AudienceFamiliarity,
    PrimaryGoal,
    Stance,
    TargetAudience,
    TonePreference,
)


class ContextBundle(BaseModel):
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
    target_audience: TargetAudience
    audience_familiarity: AudienceFamiliarity | None = None
    detail_level: DetailLevel | None = None
    tone_preference: TonePreference
    stance: Stance = "balanced"
    primary_goal: PrimaryGoal | None = None
    desired_action: DesiredAction | None = None
    voice_profile_id: str
    constraints: dict | None = None
    distribution_targets: list[DistributionTarget] | None = None


# Backward-compatible alias used across existing code paths.
ContextBundleV1 = ContextBundle


