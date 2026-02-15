import json
from pathlib import Path

from src.contracts.prd import (
    ContentVersionEntity,
    ContentVersionListResponse,
    DistributionRequest,
    DistributionResponse,
    EditorialRequest,
    EditorialResponse,
    GitHubOutput,
    InstagramOutput,
    LinkedInOutput,
    MasterContentResponse,
    MediumOutput,
    PlatformOutputEntity,
    PlatformOutputListResponse,
    ProjectEntity,
    ResearchTrendResponse,
    SubstackOutput,
    TopicInitializationRequest,
    TopicInitializationResponse,
    XOutput,
    YouTubeOutput,
)


def _load(name: str) -> dict:
    base = Path(__file__).resolve().parents[2] / "contracts" / "examples"
    return json.loads((base / name).read_text(encoding="utf-8"))


def test_contract_examples_validate() -> None:
    TopicInitializationRequest.model_validate(_load("node0_topic_initialization.request.json"))
    TopicInitializationResponse.model_validate(_load("node0_topic_initialization.response.json"))
    ResearchTrendResponse.model_validate(_load("node1_research_trend.response.json"))
    MasterContentResponse.model_validate(_load("node2_master_content.response.json"))
    EditorialRequest.model_validate(_load("node3_editorial.request.json"))
    EditorialResponse.model_validate(_load("node3_editorial.response.json"))
    LinkedInOutput.model_validate(_load("adapter_linkedin.response.json"))
    XOutput.model_validate(_load("adapter_x.response.json"))
    YouTubeOutput.model_validate(_load("adapter_youtube.response.json"))
    InstagramOutput.model_validate(_load("adapter_instagram.response.json"))
    SubstackOutput.model_validate(_load("adapter_substack.response.json"))
    MediumOutput.model_validate(_load("adapter_medium.response.json"))
    GitHubOutput.model_validate(_load("adapter_github.response.json"))
    DistributionRequest.model_validate(_load("distribution.request.json"))
    DistributionResponse.model_validate(_load("distribution.response.json"))
    ProjectEntity.model_validate(_load("entity_project.json"))
    ContentVersionEntity.model_validate(_load("entity_content_version.json"))
    PlatformOutputEntity.model_validate(_load("entity_platform_output.json"))
    ContentVersionListResponse.model_validate(_load("api_versions_list.response.json"))
    PlatformOutputListResponse.model_validate(_load("api_platform_outputs_list.response.json"))
