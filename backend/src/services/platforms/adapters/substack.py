from src.services.platforms.contracts import PlatformAdapter


class SubstackAdapter(PlatformAdapter):
    platform = "substack"

    def transform(self, master_document: str, context: dict) -> dict:
        topic = (context.get("topic_title") or context.get("normalized_topic") or "AI").strip()
        article = (master_document or "").strip()
        if not article.startswith("#"):
            article = f"# {topic}\n\n{article}"
        return {"substack_article": article, "summary_intro": f"Weekly deep dive: {topic}."}
