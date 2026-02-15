from src.services.platforms.contracts import PlatformAdapter


class GitHubAdapter(PlatformAdapter):
    platform = "github"

    def transform(self, master_document: str, context: dict) -> dict:
        topic = (context.get("topic_title") or context.get("normalized_topic") or "AI").strip()
        return {
            "readme": f"# {topic}\n\n## Problem\nOne post cannot fit every platform.\n\n## Solution\nUse a DAG with a master document.",
            "architecture_diagram_prompt": "DAG: topic -> research -> master -> adapters -> publish",
        }
