from src.services.platforms.contracts import PlatformAdapter


class YouTubeAdapter(PlatformAdapter):
    platform = "youtube"

    def transform(self, master_document: str, context: dict) -> dict:
        topic = (context.get("topic_title") or context.get("normalized_topic") or "AI").strip()
        return {
            "youtube_script": f"Title: {topic}\n\n{(master_document or '').strip()}",
            "chapters": ["Hook", "Problem", "Approach", "Conclusion"],
            "seo_description": f"Practical guide on {topic}.",
        }
