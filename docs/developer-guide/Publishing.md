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
- `POST /api/v1/publishing/save-to-publish`
  - saves mapped platform payload as files/folder bundle via adapter output logic
- `GET /api/v1/publishing/output-path/browse`
  - backend-host filesystem browser helper for UI
- `POST /api/v1/publishing/output-path/pick-local`
  - opens native folder picker on backend host machine and returns selected path
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

`save_to_publish` path:
1. Validates platform/project/user_name/output path
2. Resolves mappings exactly like publish flow
3. Calls adapter `build_platform_payload(...)`
4. Calls adapter `save_to_publish_bundle(...)` when present
5. Persists `publish_jobs` row with status `saved` and output snapshot
6. Returns saved output location

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

## Output path behavior

Output root can be:
- local filesystem path or `file://` path
- `azure://<container>/<prefix>` (or `az://...`)
- `gs://<bucket>/<prefix>`

Folder structure used by save-to-publish:
- `Publishr/<user_id>/<project_id>/<platform>_<user_name>`

Adapters write final files under this relative path.

### Output-related config

- `OUTPUT_PATH` (optional fallback when UI does not send output path)
- `AZURE_STORAGE_CONNECTION_STRING` (required for `azure://` or `az://`)
- Google credentials must be available in runtime environment for `gs://` (via standard GCP auth chain)

### Local picker caveat

`POST /api/v1/publishing/output-path/pick-local` opens a native folder picker on the backend host machine.
In remote deployments, this is not the end-user device file system.

## UI status (current)

React UI (`ui/react/src/App.jsx`) includes a `Publish` page that can:
- load dynamic platform list + field schema
- map artifact sources to platform fields
- trigger `Save to Publish` (name + output location)
- call native folder picker via backend endpoint for local path selection

Current limitation:
- final publish API flow remains adapter-dependent; LinkedIn API call path is intentionally disabled in adapter while Save-to-Publish is primary.

## Operational notes

- Adapter list is dynamic: adding/removing adapter files changes `GET /platforms` output after backend restart.
- The schema file was renamed to `publishing_schemas.py` to avoid confusion with the publishing service module.
- Keep API schemas (`schemas/`) and service logic (`services/`) separate; do not merge them.
