from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


AudiencePrimarySegment = Literal[
    "general",
    "professionals",
    "creators_influencers",
    "small_business_owners",
    "founders_entrepreneurs",
    "builders_developers",
    "marketing_growth",
    "sales_partnerships",
    "enterprise_leaders",
    "other",
]
DetailLevel = Literal["quick_take", "practical", "deep_dive"]
TonePreference = Literal["professional", "analytical", "conversational"]
DistributionTarget = Literal["linkedin", "x", "youtube", "instagram", "substack", "medium", "github"]
AudienceFamiliarity = Literal["new", "somewhat_familiar", "very_familiar"]
Stance = Literal["neutral", "supportive", "contrarian", "balanced"]
PrimaryGoal = Literal["educate", "thought_leadership", "promote", "entertain", "recruit", "community", "convert"]
DesiredAction = Literal["comment", "share", "follow", "click", "dm", "subscribe", "buy"]


class TargetAudience(ContractModel):
    primary_segment: AudiencePrimarySegment
    notes: str | None = None


class TopicInitializationRequest(ContractModel):
    project_id: str
    topic_title: str
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


class TopicInitializationResponse(ContractModel):
    project_id: str
    normalized_topic: str
    context_bundle: dict


class ResearchTrendResponse(ContractModel):
    research_summary: str
    emerging_tools: list[str]
    recent_discussions: list[str]
    key_insights: list[str]
    contrarian_angles: list[str]


class MasterContentVariant(ContractModel):
    label: str
    master_document: str
    structure_outline: list[str]
    core_arguments: list[str]


class MasterContentResponse(ContractModel):
    master_document: str
    structure_outline: list[str]
    core_arguments: list[str]
    master_variants: list[MasterContentVariant] | None = None


EditorialActionType = Literal["rewrite", "expand", "shorten", "simplify", "optimize"]


class EditorialAction(ContractModel):
    action: EditorialActionType
    target_section: str


class EditorialRequest(ContractModel):
    project_id: str
    current_version: int
    editor_actions: list[EditorialAction]
    user_feedback: str


class EditorialResponse(ContractModel):
    draft_version: int
    updated_master_document: str
    change_log: list[str]


class LinkedInPost(ContractModel):
    body: str
    hashtags: list[str]
    carousel_slides: list[str]


class LinkedInOutput(ContractModel):
    linkedin_post: LinkedInPost


class XOutput(ContractModel):
    x_thread: list[str]
    engagement_hook: str


class YouTubeOutput(ContractModel):
    youtube_script: str
    chapters: list[str]
    seo_description: str


class InstagramOutput(ContractModel):
    reel_script: str
    visual_sequence: list[str]
    hashtags: list[str]


class SubstackOutput(ContractModel):
    substack_article: str
    summary_intro: str


class MediumOutput(ContractModel):
    medium_article: str
    seo_keywords: list[str]
    tags: list[str]


class GitHubOutput(ContractModel):
    readme: str
    architecture_diagram_prompt: str


PublishStatus = Literal["scheduled", "published", "failed"]


class DistributionRequest(ContractModel):
    platform: str
    content_payload: dict
    scheduled_time: str | None = None


class DistributionResponse(ContractModel):
    status: PublishStatus
    external_id: str | None


ProjectStatus = Literal["draft", "ready", "published"]
ContentVersionKind = Literal["base", "variant", "editorial"]
ArtifactKind = Literal["text", "image", "video", "audio", "gif", "bundle"]
ArtifactFormat = str


class ProjectEntity(ContractModel):
    project_id: str
    status: ProjectStatus
    final_version_number: int | None = None
    finalized_at: str | None = None
    created_at: str


class ContentVersionEntity(ContractModel):
    version_id: str
    project_id: str
    version_number: int
    version_kind: ContentVersionKind | None = None
    variant_label: str | None = None
    keywords: list[str] = Field(default_factory=list)
    structure_outline: list[str] = Field(default_factory=list)
    version_stage: Literal["draft", "final"] = "draft"
    source_version_number: int | None = None
    updated_at: str | None = None
    content: str


class PlatformOutputEntity(ContractModel):
    platform: str
    format_type: str
    content: str
    optimized: bool


class ContentVersionListResponse(ContractModel):
    project_id: str
    versions: list[ContentVersionEntity]


class PlatformOutputListResponse(ContractModel):
    project_id: str
    outputs: list[PlatformOutputEntity]


class ArtifactEntity(ContractModel):
    artifact_id: str
    project_id: str
    format: ArtifactFormat
    kind: ArtifactKind
    title: str | None = None
    payload_json: dict = Field(default_factory=dict)
    tags_json: list[str] = Field(default_factory=list)
    status: str = "generated"
    revision: int = 1
    parent_artifact_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ArtifactListResponse(ContractModel):
    project_id: str
    artifacts: list[ArtifactEntity]
