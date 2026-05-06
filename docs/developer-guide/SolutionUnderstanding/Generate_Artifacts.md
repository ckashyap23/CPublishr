# Generate Artifacts

Artifact generation turns finalized editorial content into text, image, video, GIF, or bundle-ready records.

## Runtime Surface

| Purpose | Endpoint |
|---------|----------|
| Generate selected artifacts | `POST /api/v1/artifacts/generate` |
| Legacy workflow artifact path | `POST /api/v1/workflows/nodes/artifacts/generate` |
| List available formats | `GET /api/v1/artifacts/catalog/formats` |
| List project artifacts | `GET /api/v1/artifacts/{project_id}` |
| Rename artifact | `PATCH /api/v1/artifacts/item/{artifact_id}/title` |

Main implementation:

- `backend/src/services/orchestration/artifacts/`
- `backend/src/services/orchestration/artifacts/formats/`
- `backend/src/api/v1/endpoints/artifacts.py`

## Builder Registry

Each artifact format is implemented by a builder module under:

```text
backend/src/services/orchestration/artifacts/formats/
```

Each module must export:

```python
BUILDER = YourBuilder()
```

The registry imports modules and discovers builders through `module.BUILDER`.

## Builder Contract

A builder must define:

- `kind`
- `formats`
- `build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft`

Example shape:

```python
class MyBuilder:
    kind = "text"
    formats = {"thread"}

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        ...

BUILDER = MyBuilder()
```

## Pipeline Context

Builders receive `PipelineContext` from:

```text
backend/src/services/orchestration/artifacts/contracts.py
```

Common fields:

- `project_id`
- `topic_title`
- `core_idea`
- `master_body`
- `seed_keywords`
- `target_audience`
- `detail_level`
- `tone_preference`
- `style_settings`
- `style_settings_by_kind`
- `style_settings_by_format`

`style_settings` is the effective merged settings object for the current format.

## Current Formats

| Kind | Formats |
|------|---------|
| `text` | `caption`, `post`, `newsletter`, `blog`, `script_short`, `cta_variants` |
| `image` | `post_image`, `thumbnail`, `banner`, `cover` |
| `video` | `gif`, `reel`, `short_video` |

## Artifact Output

Builders return `ArtifactDraft`:

- `format`
- `title`
- `payload_json`
- `tags_json`
- optional `status`
- optional `revision`
- optional `parent_artifact_id`

Use the shared envelope:

```json
{
  "version": "1.0",
  "body": null,
  "items": [],
  "assets": [],
  "prompts": [],
  "settings": {},
  "notes": null
}
```

## Style Settings

Requests can send:

- `style_settings_by_kind`
- `style_settings_by_format`

Effective format settings are resolved as:

1. kind-level settings for the format kind
2. format-level overrides for the exact format

Image and video builders also read `include_master_content` to decide whether to include master content context in prompts.

## Media Persistence

Text drafts are persisted normally.

Media drafts for `image`, `video`, and `gif` are persisted only when:

```python
draft.status == "generated"
```

Failed, partial, or simulated media drafts are skipped.

## Adding a Format

1. Add a module under `backend/src/services/orchestration/artifacts/formats/`.
2. Implement a builder and export `BUILDER`.
3. Set the correct `kind` and `formats`.
4. Return a valid artifact envelope.
5. Restart the backend.
6. Verify the catalog and generation endpoint:

```bash
GET /api/v1/artifacts/catalog/formats
POST /api/v1/artifacts/generate
```

Also confirm the React Artifact Generator shows the new format.
