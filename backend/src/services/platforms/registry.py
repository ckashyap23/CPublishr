from src.services.platforms.adapters.github import GitHubAdapter
from src.services.platforms.adapters.instagram import InstagramAdapter
from src.services.platforms.adapters.linkedin import LinkedInAdapter
from src.services.platforms.adapters.medium import MediumAdapter
from src.services.platforms.adapters.substack import SubstackAdapter
from src.services.platforms.adapters.x import XAdapter
from src.services.platforms.adapters.youtube import YouTubeAdapter


def default_platform_registry() -> dict[str, object]:
    return {
        "linkedin": LinkedInAdapter(),
        "x": XAdapter(),
        "youtube": YouTubeAdapter(),
        "instagram": InstagramAdapter(),
        "substack": SubstackAdapter(),
        "medium": MediumAdapter(),
        "github": GitHubAdapter(),
    }
