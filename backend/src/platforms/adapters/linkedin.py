from __future__ import annotations

from typing import Any


class LinkedInAdapter:
    platform_name = "linkedin"

    @staticmethod
    def _artifact_part_value(source: dict[str, Any]) -> Any:
        artifact = source.get("artifact") if isinstance(source, dict) else {}
        if not isinstance(artifact, dict):
            return None
        part = str(source.get("part") or "").strip()
        if part == "title":
            return artifact.get("title")
        if part == "tags_json":
            return artifact.get("tags_json") or []
        payload = artifact.get("payload_json") if isinstance(artifact.get("payload_json"), dict) else {}
        if part == "body":
            return payload.get("body")
        if part == "items":
            return payload.get("items") or []
        if part == "assets":
            return payload.get("assets") or []
        return None

    @staticmethod
    def _render_source_preview(source: dict[str, Any]) -> str:
        value = LinkedInAdapter._artifact_part_value(source)
        render_as = str(source.get("render_as") or "").strip().lower()
        part = str(source.get("part") or "").strip().lower()
        if part == "tags_json":
            tags = [str(x).strip() for x in (value or []) if str(x).strip()]
            if render_as == "hashtags_line":
                tags = [t if t.startswith("#") else f"#{t.replace(' ', '')}" for t in tags]
            return " ".join(tags)
        if isinstance(value, list):
            return "\n".join(str(x) for x in value if str(x).strip())
        return str(value or "").strip()

    def get_field_schema(self) -> dict[str, Any]:
        return {
            "platform": self.platform_name,
            "fields": [
                {
                    "field_key": "body",
                    "label": "LinkedIn Body",
                    "required": True,
                    "allows_multiple": False,
                    "accepted_artifact_formats": ["post"],
                    "description": "Main LinkedIn post body (post artifact body + tags/hashtags may be merged in adapter).",
                    "suggested_parts": ["body", "tags_json", "title"],
                },
                {
                    "field_key": "image",
                    "label": "LinkedIn Image",
                    "required": False,
                    "allows_multiple": True,
                    "accepted_artifact_formats": ["post_image"],
                    "description": "Optional LinkedIn image asset.",
                    "suggested_parts": ["assets"],
                },
                {
                    "field_key": "video",
                    "label": "LinkedIn Video",
                    "required": False,
                    "allows_multiple": False,
                    "accepted_artifact_formats": ["video"],
                    "description": "Optional LinkedIn video asset.",
                    "suggested_parts": ["assets"],
                },
                {
                    "field_key": "document",
                    "label": "LinkedIn Document",
                    "required": False,
                    "allows_multiple": False,
                    "accepted_artifact_formats": [""],
                    "description": "Optional LinkedIn document.",
                    "suggested_parts": [""],
                },
            ],
        }

    def build_platform_payload(self, *, field_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        # Placeholder composition behavior using source-level mapping (artifact + part + render_as).
        body_sources = field_mapping.get("body") or []
        image_sources = field_mapping.get("image") or []
        body_text = "\n\n".join(
            [chunk for chunk in (self._render_source_preview(s) for s in body_sources) if chunk]
        ).strip()
        image_source = image_sources[0] if image_sources else None
        return {
            "platform": self.platform_name,
            "linkedin_body": body_text,
            "linkedin_body_sources": body_sources,
            "linkedin_image_source": image_source,
        }

    def publish(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        # Placeholder publish. Replace with actual LinkedIn API integration.
        return {
            "status": "published",
            "external_id": "linkedin_placeholder_post_id",
            "external_url": None,
            "provider_response": {"mode": "placeholder"},
            "payload": payload,
        }


ADAPTER = LinkedInAdapter()
