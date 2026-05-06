# Generate Adapter

Use this guide to add a platform adapter for the Publish stage.

## Where Adapters Live

Add a module:

```text
backend/src/platforms/adapters/<platform>.py
```

The registry auto-discovers modules in:

```text
backend/src/platforms/adapters/registry.py
```

Each adapter module must export:

```python
ADAPTER = YourAdapter()
```

Restart the backend after adding or renaming adapter files.

## Required Adapter API

Each adapter must implement:

```python
def get_field_schema(self) -> list[dict]: ...
def build_platform_payload(self, *, field_mapping: dict[str, list[dict]]) -> dict: ...
def publish(self, *, payload: dict) -> dict: ...
```

Recommended for Save-to-Publish:

```python
def save_to_publish_bundle(
    self,
    *,
    payload: dict,
    output_root: str,
    relative_path: str,
) -> dict: ...
```

If `save_to_publish_bundle` exists, `POST /api/v1/publishing/save-to-publish` delegates file assembly to the adapter.

## Field Schema

`get_field_schema()` drives the React mapping UI and backend validation.

Each field should include:

- `field_key`
- `label`
- `required`
- `allows_multiple`
- `accepted_artifact_formats`
- `description`
- `suggested_parts`

Example:

```json
{
  "field_key": "body",
  "label": "Post body",
  "required": true,
  "allows_multiple": true,
  "accepted_artifact_formats": ["post", "caption", "newsletter"],
  "description": "Primary platform text.",
  "suggested_parts": ["body", "items", "tags_json"]
}
```

## Mapping Input

`PublishingService` validates the UI mapping, loads artifacts, and passes resolved sources to the adapter:

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
        "tags_json": ["#example"]
      }
    }
  ]
}
```

## Adapter Responsibilities

Adapters own platform-specific composition:

- Join text parts into final platform text.
- Normalize media assets.
- Convert tags/hashtags.
- Shape payloads for platform APIs or file bundles.

Adapters do not own:

- Auth user scoping
- Artifact loading
- Generic mapping validation
- Publish job persistence
- Scheduling or retry policy

## Existing Adapters

| Adapter | Current behavior |
|---------|------------------|
| `linkedin.py` | Field schema, payload composition, Save-to-Publish bundle; direct publish intentionally disabled |
| `instagram.py` | Field schema, payload composition, Save-to-Publish bundle; direct publish placeholder |

## Verification

After adding an adapter:

```bash
GET /api/v1/publishing/platforms
GET /api/v1/publishing/platforms/{platform}/fields
POST /api/v1/publishing/jobs/artifacts
POST /api/v1/publishing/save-to-publish
```

Also verify the React Publish page can load the platform and map at least one generated artifact.
