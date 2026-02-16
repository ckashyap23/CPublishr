from typing import Literal

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


TargetAudience = Literal["builders", "founders", "enterprise", "general tech"]
ContentDepth = Literal["surface", "intermediate", "deep"]
TonePreference = Literal["professional", "analytical", "conversational"]
DistributionTarget = Literal["linkedin", "x", "youtube", "instagram", "substack", "medium", "github"]


class TopicInitializationRequest(ContractModel):
    project_id: str
    topic_title: str
    core_idea: str
    user_content: str | None = None
    target_audience: TargetAudience | None = None
    content_depth: ContentDepth | None = None
    tone_preference: TonePreference
    distribution_targets: list[DistributionTarget]


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


class MasterContentResponse(ContractModel):
    master_document: str
    structure_outline: list[str]
    core_arguments: list[str]


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


class ProjectEntity(ContractModel):
    project_id: str
    status: ProjectStatus
    created_at: str


class ContentVersionEntity(ContractModel):
    version_id: str
    project_id: str
    version_number: int
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
