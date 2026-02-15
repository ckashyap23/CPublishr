from src.services.platforms.contracts import PlatformAdapter


class MediumAdapter(PlatformAdapter):
    platform = "medium"

    def transform(self, master_document: str, context: dict) -> dict:
        topic = (context.get("topic_title") or context.get("normalized_topic") or "AI").strip()
        article = (master_document or "").strip()
        if not article.startswith("#"):
            article = f"# {topic}\n\n{article}"
        return {"medium_article": article, "seo_keywords": [topic, "ai", "content workflows"], "tags": ["AI", "Content Strategy", "Engineering"]}
