# Generate Adapter (Publish Platform Adapter Guide)

This guide describes how to add a new platform adapter for the `Publish` stage.
For runtime behavior, endpoint details, and save-to-publish flow, refer to `docs/teamwork/Publishing.md`.

## Location and discovery

Add file:
- `backend/src/platforms/adapters/<platform>.py`

Registry:
- `backend/src/platforms/adapters/registry.py` auto-discovers modules exporting `ADAPTER`.

## Required adapter methods

Each adapter must implement:
- `get_field_schema() -> dict`
- `build_platform_payload(*, field_mapping: dict[str, list[dict]]) -> dict`
- `publish(*, payload: dict) -> dict`

Optional but recommended:
- `save_to_publish_bundle(*, payload: dict, output_root: str, relative_path: str) -> dict`

If `save_to_publish_bundle` exists, `POST /api/v1/publishing/save-to-publish` delegates final output assembly and file writing to the adapter.

## Field schema contract

Returned by `get_field_schema()` and used by UI mapping page.

Per field include:
- `field_key`
- `label`
- `required`
- `allows_multiple`
- `accepted_artifact_formats`
- `description`
- `suggested_parts`

## Mapping contract passed to adapter

Publishing service resolves mappings into artifact-aware sources and passes:

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

Keep it in adapters, not UI:
- join text parts (body/items/tags) for platform text fields
- choose and normalize media assets
- convert tags to platform-specific hashtag shape

UI should only collect mappings.

## Current implementation notes (brief)

- `linkedin.py`: schema + composition + save-to-publish bundle; publish path intentionally disabled.
- `instagram.py`: schema + composition + save-to-publish bundle; publish remains placeholder.

## Validation handled by service (before adapter)

`PublishingService` validates:
- field key exists in adapter schema
- required fields are mapped
- artifact exists in project
- artifact format is allowed for target field

## Quick checklist

1. Add adapter file and export `ADAPTER`
2. Implement schema and payload composition
3. Add `save_to_publish_bundle` if Save-to-Publish should output files/folders
4. Keep `publish` as placeholder or real integration
5. Restart backend
6. Verify:
   - `GET /api/v1/publishing/platforms`
   - `GET /api/v1/publishing/platforms/{platform}/fields`
   - `POST /api/v1/publishing/save-to-publish`
   - `POST /api/v1/publishing/jobs/artifacts`
