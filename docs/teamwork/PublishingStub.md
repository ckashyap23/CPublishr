# Publishing Stub - Current State and Roadmap

This document captures the latest publishing implementation and the remaining path to full platform publishing.

## Current Implementation (As of Now)

Primary service:
- `backend/src/services/publishing/service.py`

Endpoint:
- `POST /api/v1/publishing/jobs`
- File: `backend/src/api/v1/endpoints/publishing.py`

### What the stub now does (Phase 1 implemented)

1. Validates request contract (`DistributionRequest`).
2. Requires `content_payload.project_id`.
3. Ensures project exists.
4. Fetches latest generated adapter output for `(project_id, platform)` from `platform_outputs`.
5. Fails fast with `400` if no publishable output exists.
6. Creates a publish job with metadata linked to the adapter output.
7. Returns stub success response:
   - `status = "published"`
   - generated `external_id`

## Phase 1 Changes Already Implemented

### 1) PublishingService now links to real adapter output
- File: `backend/src/services/publishing/service.py`
- Added logic to read latest output by `project_id + platform`.
- Added validation that output exists before job creation.

### 2) Content repository helper added
- File: `backend/src/db/repositories/content_repository.py`
- Added:
  - `get_latest_platform_output(project_id, platform)`

### 3) Publish job model expanded
- File: `backend/src/db/models/publish_job.py`
- Added columns:
  - `platform_output_id: str | None`
  - `payload_snapshot: str` (JSON serialized)

### 4) Publish repository supports metadata
- File: `backend/src/db/repositories/publish_repository.py`
- `create_job(...)` now accepts:
  - `platform_output_id`
  - `payload_snapshot`

### 5) API returns clean validation errors
- File: `backend/src/api/v1/endpoints/publishing.py`
- Catches service `ValueError` and returns HTTP `400`.

## Data Flow (Current)

1. Adapters generate platform output during workflow run and store in `platform_outputs`.
2. Publish API receives platform + project reference.
3. Publishing service selects latest matching platform output.
4. Publish job is recorded with snapshot + output reference.
5. Stub returns immediate published response (no external API call yet).

## Important DB Note

Because `publish_jobs` schema changed, existing tables may need migration.

Startup now runs a lightweight Postgres compatibility patch (`ALTER TABLE ... IF NOT EXISTS`) for recent added columns.
For larger schema changes, still use explicit migrations.

## Remaining Work to Reach Real Publishing

## Phase 2: OAuth and credential lifecycle

Add:
- OAuth connect/callback/disconnect endpoints
- secure token storage (encrypted at rest)
- token refresh handling

Likely files:
- `backend/src/services/publishing/oauth.py` (or provider-specific modules)
- new/updated DB model for oauth connections

## Phase 3: Platform API clients

Add client modules per platform:
- LinkedIn, X, YouTube, Instagram, Substack, Medium, GitHub

Each client should include:
- payload mapping
- auth handling
- response normalization
- error normalization

## Phase 4: Async execution, retries, idempotency

Add:
- job state machine: `scheduled -> running -> published/failed`
- worker/queue execution
- exponential backoff retries
- idempotency keys

## Phase 5: Publish dashboard and operational APIs

Add endpoints for:
- list/filter jobs
- retry failed jobs
- cancel scheduled jobs
- inspect external IDs and links

## Contract and Coordination Rules

- Keep `DistributionRequest` / `DistributionResponse` stable unless coordinated.
- If schema changes are needed, update all:
  1. `backend/src/contracts/prd.py`
  2. `backend/contracts/examples/*.json`
  3. `backend/tests/unit/test_prd_contract_examples.py`

## Done Criteria for Full Publishing

- OAuth connections established securely.
- Real platform API publishing works.
- Publish jobs store normalized external metadata.
- Retry/idempotency prevent duplicate posting.
- Dashboard/API visibility supports troubleshooting and operations.
