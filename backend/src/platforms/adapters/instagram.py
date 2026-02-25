from __future__ import annotations

from typing import Any


class InstagramAdapter:
    platform_name = "instagram"

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
        value = InstagramAdapter._artifact_part_value(source)
        render_as = str(source.get("render_as") or "").strip().lower()
        part = str(source.get("part") or "").strip().lower()
        if part == "tags_json":
            tags = [str(x).strip() for x in (value or []) if str(x).strip()]
            if render_as in {"hashtags_line", "hashtags_block"}:
                tags = [t if t.startswith("#") else f"#{t.replace(' ', '')}" for t in tags]
            sep = "\n" if render_as == "hashtags_block" else " "
            return sep.join(tags)
        if part == "items" and isinstance(value, list):
            # Typical CTA/script items payload: [{"text": "..."}]
            texts = [str(v.get("text") or "").strip() for v in value if isinstance(v, dict)]
            texts = [t for t in texts if t]
            return "\n".join(texts)
        if isinstance(value, list):
            return "\n".join(str(x) for x in value if str(x).strip())
        return str(value or "").strip()

    def get_field_schema(self) -> dict[str, Any]:
        return {
            "platform": self.platform_name,
            "fields": [
                {
                    "field_key": "caption",
                    "label": "Instagram Caption",
                    "required": True,
                    "allows_multiple": True,
                    "accepted_artifact_formats": ["caption"],
                    "description": "Primary Instagram caption text (can combine caption + CTA variants/tags via source mapping).",
                    "suggested_parts": ["body", "tags_json"],
                },
                {
                    "field_key": "cta_variants",
                    "label": "CTA Variants",
                    "required": False,
                    "allows_multiple": True,
                    "accepted_artifact_formats": ["cta_variants"],
                    "description": "Optional CTA variants to append/select from.",
                    "suggested_parts": ["items"],
                },
                {
                    "field_key": "image",
                    "label": "Instagram Image",
                    "required": True,
                    "allows_multiple": False,
                    "accepted_artifact_formats": ["post_image"],
                    "description": "Instagram post image.",
                    "suggested_parts": ["assets"],
                },
            ],
        }

    def build_platform_payload(self, *, field_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        # Placeholder composition behavior using source-level mapping (artifact + part + render_as).
        caption_sources = field_mapping.get("caption") or []
        cta_sources = field_mapping.get("cta_variants") or []
        image_sources = field_mapping.get("image") or []
        caption_text = "\n\n".join(
            [chunk for chunk in (self._render_source_preview(s) for s in caption_sources) if chunk]
        ).strip()
        cta_text = "\n".join(
            [chunk for chunk in (self._render_source_preview(s) for s in cta_sources) if chunk]
        ).strip()
        return {
            "platform": self.platform_name,
            "instagram_caption": caption_text,
            "instagram_caption_sources": caption_sources,
            "instagram_cta_text": cta_text or None,
            "instagram_cta_sources": cta_sources,
            "instagram_image_source": (image_sources[0] if image_sources else None),
        }

    def publish(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        # Placeholder publish. Replace with actual Instagram API integration.
        return {
            "status": "published",
            "external_id": "instagram_placeholder_media_id",
            "external_url": None,
            "provider_response": {"mode": "placeholder"},
            "payload": payload,
        }


ADAPTER = InstagramAdapter()
