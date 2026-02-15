from src.services.platforms.contracts import PlatformAdapter


class LinkedInAdapter(PlatformAdapter):
    platform = "linkedin"

    def transform(self, master_document: str, context: dict) -> dict:
        body = "\n".join((master_document or "").splitlines()[:10]).strip()
        return {"linkedin_post": {"body": body or "Practical AI workflow notes.", "hashtags": ["#ai", "#content", "#builders"], "carousel_slides": []}}
