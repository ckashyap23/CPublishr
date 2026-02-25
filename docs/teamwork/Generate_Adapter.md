# Generate Adapter (Publish Platform Adapter Guide)

This guide explains how to add a new publish-platform adapter for the `Publish` workflow stage.

## Where to add the adapter

Create a new file under:
- `backend/src/platforms/adapters/`

Example:
- `backend/src/platforms/adapters/x.py`

The adapter registry auto-discovers modules in this folder that export `ADAPTER`.

## Required adapter methods

Your adapter must expose a module-level `ADAPTER` instance with these methods:
- `get_field_schema() -> dict`
- `build_platform_payload(*, field_mapping: dict[str, list[dict]]) -> dict`
- `publish(*, payload: dict) -> dict`

Minimal shape:

```python
from __future__ import annotations
from typing import Any


class XAdapter:
    platform_name = "x"

    def get_field_schema(self) -> dict[str, Any]:
        return {
            "platform": self.platform_name,
            "fields": [
                {
                    "field_key": "body",
                    "label": "Post Body",
                    "required": True,
                    "allows_multiple": True,
                    "accepted_artifact_formats": ["post"],
                    "description": "Main post body text.",
                    "suggested_parts": ["body", "tags_json", "title"],
                }
            ],
        }

    def build_platform_payload(self, *, field_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        return {"platform": self.platform_name, "payload_preview": field_mapping}

    def publish(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "published", "external_id": "placeholder", "external_url": None, "payload": payload}


ADAPTER = XAdapter()
```

## Field schema (drives the UI)

`get_field_schema()` is used by:
- `GET /api/v1/publishing/platforms/{platform}/fields`
- React `Publish` UI mapping screen

Each field object should define:
- `field_key` (stable key used in request payload)
- `label` (UI label)
- `required` (`true/false`)
- `allows_multiple` (`true/false`) for source rows
- `accepted_artifact_formats` (artifact formats allowed for this field)
- `description` (short UI help text)
- `suggested_parts` (optional; hints such as `body`, `tags_json`, `items`, `assets`)

## Mapping contract (what `build_platform_payload` receives)

The publish API sends `field_mappings` as `sources[]`.

Each source row includes:
- `artifact_id`
- `part`
- `render_as` (optional adapter hint)
- `order`

The publish service resolves artifacts and passes adapters:

```json
{
  "body": [
    {
      "artifact_id": "art_123",
      "part": "body",
      "render_as": null,
      "order": 0,
      "artifact": {
        "artifact_id": "art_123",
        "format": "post",
        "title": "Example",
        "payload_json": { "body": "...", "items": [], "assets": [] },
        "tags_json": ["#a", "#b"]
      }
    }
  ]
}
```

## Where composition logic should live

Platform-specific combining logic belongs in the adapter:
- combine `post.body + tags_json` for LinkedIn
- combine `caption.body + cta_variants.items` for Instagram
- convert tags to hashtag line/block based on `render_as`

Do not push platform composition logic into the UI.

## Current publish flow (backend)

1. UI loads platform list (`/api/v1/publishing/platforms`)
2. UI loads field schema (`/api/v1/publishing/platforms/{platform}/fields`)
3. UI sends mapping (`POST /api/v1/publishing/jobs/artifacts`)
4. `PublishingService` validates + resolves artifacts
5. Adapter builds platform payload
6. Adapter `publish()` is called
7. `publish_jobs` row is created with `publish_job_id`

## Checklist when adding a new adapter

1. Create `backend/src/platforms/adapters/<platform>.py`
2. Export `ADAPTER`
3. Implement `get_field_schema()`
4. Implement `build_platform_payload()` using source-part mappings
5. Implement placeholder `publish()` first (real API later)
6. Restart backend
7. Verify:
   - `GET /api/v1/publishing/platforms` lists your platform
   - `GET /api/v1/publishing/platforms/{platform}/fields` returns your schema
   - Platform appears in UI `Publish` page dropdown
   - Field mapping UI loads and payload preview looks correct
