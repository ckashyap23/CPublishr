from src.services.platforms.contracts import PlatformAdapter


class InstagramAdapter(PlatformAdapter):
    platform = "instagram"

    def transform(self, master_document: str, context: dict) -> dict:
        topic = (context.get("topic_title") or context.get("normalized_topic") or "AI").strip()
        return {"reel_script": f"Quick breakdown: {topic} in 3 steps.", "visual_sequence": ["Hook", "Steps", "CTA"], "hashtags": ["#ai", "#content", "#creators", "#automation", "#startup"]}
