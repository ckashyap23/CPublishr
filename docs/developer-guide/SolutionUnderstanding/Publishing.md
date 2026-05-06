# Publishing

Publishing maps generated artifacts into platform-specific payloads through adapters.

## Main Files

| Layer | File |
|-------|------|
| API endpoints | `backend/src/api/v1/endpoints/publishing.py` |
| API schemas | `backend/src/schemas/publishing_schemas.py` |
| Service | `backend/src/services/publishing/service.py` |
| Adapter registry | `backend/src/platforms/adapters/registry.py` |
| Adapters | `backend/src/platforms/adapters/*.py` |

Keep schemas in `schemas/` and business logic in `services/`.

## Runtime Surface

| Purpose | Endpoint |
|---------|----------|
| List platforms | `GET /api/v1/publishing/platforms` |
| Get field schema | `GET /api/v1/publishing/platforms/{platform}/fields` |
| Create artifact-mapped publish job | `POST /api/v1/publishing/jobs/artifacts` |
| Save mapped output bundle | `POST /api/v1/publishing/save-to-publish` |
| Browse backend-host paths | `GET /api/v1/publishing/output-path/browse` |
| Pick local backend-host folder | `POST /api/v1/publishing/output-path/pick-local` |
| Legacy platform-output job | `POST /api/v1/publishing/jobs` |

## Request Contract

The React UI sends artifact mappings per platform field:

```json
{
  "project_id": "proj_123",
  "platform": "linkedin",
  "field_mappings": [
    {
      "field_key": "body",
      "sources": [
        { "artifact_id": "art_post", "part": "body", "order": 0 },
        { "artifact_id": "art_post", "part": "tags_json", "render_as": "hashtags_line", "order": 1 }
      ]
    }
  ]
}
```

Schema models live in:

```text
backend/src/schemas/publishing_schemas.py
```

Important models:

- `PublishFieldArtifactSource`
- `PublishFieldArtifactMapping`
- `ArtifactPublishRequest`
- `ArtifactPublishJobResponse`

## Service Responsibilities

`PublishingService` handles generic publish flow:

1. Validate project, platform, and user scope.
2. Load adapter from registry.
3. Load adapter field schema.
4. Validate required fields and accepted artifact formats.
5. Load mapped artifacts.
6. Resolve source rows into artifact snapshots.
7. Call adapter composition.
8. Call adapter publish or save-to-publish behavior.
9. Persist `publish_jobs` with payload snapshot.

Adapters handle platform-specific composition and API/file output shape.

## Save-To-Publish

Output root can be:

- local filesystem path
- `file://` path
- `azure://<container>/<prefix>`
- `az://<container>/<prefix>`
- `gs://<bucket>/<prefix>`

Output path resolution:

- UI-provided output path wins.
- `OUTPUT_PATH` is used as fallback.
- Azure output requires `AZURE_STORAGE_CONNECTION_STRING`.
- GCS output uses the standard Google Cloud auth chain.

The local folder picker runs on the backend host. In a remote deployment, that is the server filesystem, not the end user's laptop.

## Publish Jobs

Every publish/save request creates a `publish_job_id`.

`publish_jobs` stores:

- project
- platform
- status
- mapping snapshot
- adapter schema snapshot
- resolved payload snapshot
- output or publish result

This gives audit history now and leaves room for future scheduling, retries, and analytics.

## Current Adapter Status

| Adapter | Status |
|---------|--------|
| LinkedIn | Save-to-Publish implemented; direct API publish intentionally disabled |
| Instagram | Save-to-Publish implemented; direct API publish placeholder |

## Change Checklist

- Update `publishing_schemas.py` for request/response contract changes.
- Update `PublishingService` for generic validation or persistence behavior.
- Update adapters only for platform-specific field schema, composition, or API calls.
- Verify the React Publish page still loads platform fields and can save a bundle.
