from src.services.platforms.contracts import PlatformAdapter


class XAdapter(PlatformAdapter):
    platform = "x"

    def transform(self, master_document: str, context: dict) -> dict:
        lines = [ln.strip(" -") for ln in (master_document or "").splitlines() if ln.strip()]
        thread = [ln[:240] for ln in lines[:5]]
        while len(thread) < 5:
            thread.append("")
        topic = (context.get("topic_title") or context.get("normalized_topic") or "AI").strip()
        return {"x_thread": thread[:15], "engagement_hook": f"{topic} in 5 points."}
