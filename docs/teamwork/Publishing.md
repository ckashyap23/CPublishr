# Publishing (Artifact-Mapped Publish Flow)

This document captures the current publishing implementation for the `Publish` workflow stage, including API schemas, adapter-driven field mapping, and publish job tracking (`publish_job_id`).

## Current architecture (high level)

Layers:
- API endpoints: `backend/src/api/v1/endpoints/publishing.py`
- API schemas: `backend/src/schemas/publishing_schemas.py`
- Publish orchestration/service: `backend/src/services/publishing/service.py`
- Platform adapters (dynamic): `backend/src/platforms/adapters/*.py`
- Adapter registry: `backend/src/platforms/adapters/registry.py`

## API schemas (important file)

Schema file:
- `backend/src/schemas/publishing_schemas.py`

Why it matters:
- This defines the UI/backend contract for publish mapping requests and publish job responses.
- It is intentionally separate from `backend/src/services/publishing/service.py` (schemas vs business logic).

Key models:
- `PublishFieldArtifactSource`
  - `artifact_id`
  - `part`
  - `render_as` (optional)
  - `order` (optional)
- `PublishFieldArtifactMapping`
  - `field_key`
  - `sources[]`
- `ArtifactPublishRequest`
  - `project_id`
  - `platform`
  - `field_mappings[]`
  - `scheduled_time` (placeholder for future scheduling)
- `ArtifactPublishJobResponse`
  - `publish_job_id`
  - `project_id`
  - `platform`
  - `status`
  - `external_id`
  - `external_url`
  - `scheduled_time`
  - `payload_snapshot`

## Endpoint summary

Publishing endpoints:
- `GET /api/v1/publishing/platforms`
  - returns dynamic platform list discovered from adapter files
- `GET /api/v1/publishing/platforms/{platform}/fields`
  - returns adapter-defined field schema for UI mapping
- `POST /api/v1/publishing/jobs/artifacts`
  - creates a publish job using mapped artifacts + adapter payload composition
- `POST /api/v1/publishing/jobs`
  - legacy stub path using `platform_outputs` (kept for compatibility)

## Publish mapping contract (UI -> backend)

The UI sends mappings per platform field with source-level granularity.

Example:

```json
{
  "project_id": "proj_local_1",
  "platform": "linkedin",
  "field_mappings": [
    {
      "field_key": "body",
      "sources": [
        { "artifact_id": "art_post_1", "part": "body", "order": 0 },
        { "artifact_id": "art_post_1", "part": "tags_json", "render_as": "hashtags_line", "order": 1 }
      ]
    },
    {
      "field_key": "image",
      "sources": [
        { "artifact_id": "art_img_1", "part": "assets", "order": 0 }
      ]
    }
  ]
}
```

This supports common use cases such as:
- LinkedIn body = `post.body + post.tags_json`
- Instagram caption = `caption.body + cta_variants.items + caption.tags_json`

## What the publishing service does

`backend/src/services/publishing/service.py` (`PublishingService`) is the orchestration layer.

Artifact-mapped job path (`create_artifact_publish_job`) currently:
1. Validates platform + project
2. Loads adapter via registry
3. Loads adapter field schema
4. Validates each field mapping against:
   - `field_key`
   - `allows_multiple`
   - `accepted_artifact_formats`
5. Loads artifacts from DB for the user/project
6. Resolves each source row into:
   - mapping metadata (`artifact_id`, `part`, `render_as`, `order`)
   - full artifact entity snapshot
7. Calls adapter:
   - `build_platform_payload(...)`
   - `publish(...)`
8. Persists a publish job row with `publish_job_id` and payload snapshot
9. Returns `ArtifactPublishJobResponse`

## `publish_job_id` and job tracking (current + future)

Current:
- Every publish request creates a `publish_job_id`
- A job snapshot is stored (mapping + adapter field schema + resolved payload + publish result)
- This provides traceability and audit history even while publish logic is placeholder

Why `publish_job_id` matters later:
- scheduling (queued/scheduled/running/published/failed)
- retries / backoff
- debugging failures with exact mapping + payload snapshot
- analytics experiments (which artifacts were used)
- later metrics linkage (engagement tied to a job)

Recommended future status model:
- `queued`
- `scheduled`
- `running`
- `published`
- `failed`
- `cancelled`

## Adapter responsibilities (publish stage)

Platform adapter files live at:
- `backend/src/platforms/adapters/<platform>.py`

They should handle:
- platform field schema (`get_field_schema`)
- platform-specific composition (`build_platform_payload`)
- platform API calls (`publish`)

They should not own:
- publish job persistence
- generic request validation
- scheduling orchestration
- retry policy

## UI status (current)

React UI (`ui/react/src/App.jsx`) includes a `Publish` workflow page that can:
- load platforms dynamically
- load platform field schema
- load project artifacts
- build source-level mappings
- preview the payload

Current limitation:
- Final `Publish` button is intentionally disabled until adapter publish implementations are completed.

## Operational notes

- Adapter list is dynamic: adding/removing adapter files changes `GET /platforms` output after backend restart.
- The schema file was renamed to `publishing_schemas.py` to avoid confusion with the publishing service module.
- Keep API schemas (`schemas/`) and service logic (`services/`) separate; do not merge them.
