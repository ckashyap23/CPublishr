# Solution Understanding

This document reflects the current backend and React UI behavior in this repository.

## 1. Current End-to-End Workflow

The backend flow is now:
1. Node 0: Initialize topic/project context (`POST /api/v1/projects/`)
2. Node 1: Research (`/workflows/nodes/research`)
3. Node 2: Master content base + variants (`/workflows/nodes/master`)
4. Editorial is mandatory before downstream generation.
5. Artifacts are generated on-demand from the Artifact Generator UI/API (`POST /api/v1/artifacts/generate`).
6. Artifacts can now be used directly in the Publish workflow stage via platform adapters and mapping UI (`Publish` page in React UI).
7. Publish jobs are created through publish service + adapter registry (`/api/v1/publishing/*`) with payload snapshot + job ID tracking.

`POST /api/v1/workflows/runs` executes Node 0-2 and returns:
- `status = "awaiting_editorial"`

It does not auto-finalize editorial.

## 2. API Endpoints (Current)

Health:
- `GET /healthz`
- `GET /api/v1/health/`

Projects:
- `GET /api/v1/projects/` (user-scoped project list for UI dropdown)
- `POST /api/v1/projects/`
- `GET /api/v1/projects/{project_id}`

Workflow:
- `POST /api/v1/workflows/runs`
- `GET /api/v1/workflows/nodes/research/{project_id}`
- `POST /api/v1/workflows/nodes/research`
- `GET /api/v1/workflows/nodes/master/{project_id}`
- `POST /api/v1/workflows/nodes/master`

Editorial:
- `POST /api/v1/workflows/nodes/editorial`
- `POST /api/v1/workflows/nodes/editorial/session/start`
- `POST /api/v1/workflows/nodes/editorial/session/{session_id}/iterate`
- `POST /api/v1/workflows/nodes/editorial/session/{session_id}/finalize`
- `POST /api/v1/workflows/nodes/editorial/finalize-direct`
- `POST /api/v1/workflows/nodes/editorial/regenerate-outline`
- `POST /api/v1/workflows/nodes/editorial/save-inline`
- `POST /api/v1/workflows/nodes/editorial/feedback/preview`
- `POST /api/v1/workflows/nodes/editorial/finalize-selected`

Artifacts:
- `POST /api/v1/workflows/nodes/artifacts/generate`
- `POST /api/v1/artifacts/generate` (full catalog on-demand; supports `style_settings_by_kind` and `style_settings_by_format`)
- `GET /api/v1/artifacts/catalog/formats` (dynamic format catalog for UI and clients)
- `GET /api/v1/artifacts/{project_id}`
- `GET /api/v1/artifacts/{project_id}/{format}`
- `GET /api/v1/artifacts/{project_id}/kind/{kind}`
- `PATCH /api/v1/artifacts/item/{artifact_id}/title` (inline artifact rename from UI)

Versions:
- `GET /api/v1/versions/{project_id}`
- `GET /api/v1/versions/{project_id}/{version_kind}`
- `PATCH /api/v1/versions/{project_id}/{version_number}/keywords`

Platform outputs:
- `GET /api/v1/platform-outputs/{project_id}`

Publishing:
- `POST /api/v1/publishing/jobs`
- `GET /api/v1/publishing/platforms`
- `GET /api/v1/publishing/platforms/{platform}/fields`
- `POST /api/v1/publishing/jobs/artifacts`

## 3. Core Data Model

`projects`:
- `project_id`
- `status`
- `context_json` (Node 0 context bundle)
- `final_version_number`
- `finalized_at`
- `created_at`

`content_versions`:
- `version_id`
- `project_id`
- `version_number`
- `version_kind` (`base | variant | editorial`)
- `variant_label`
- `keywords_json`
- `structure_outline_json`
- `version_stage` (`draft | final`)
- `source_version_number`
- `updated_at`
- `content`

`editorial_sessions`:
- tracks temporary working content until finalized

`artifacts`:
- generated from finalized editorial content

`publish_jobs`:
- publish jobs with job ID + payload snapshot (artifact-mapped publish path and legacy stub path)

## 4. Versioning Semantics

Base/variant generation:
- Node 2 writes one `base` version and zero or more `variant` versions.

Editorial draft/final:
- Regenerate/save-inline create `editorial` drafts.
- `save-inline` accepts optional `version_label`; when provided, it is persisted as `variant_label` on the saved editorial draft.
- Finalization marks one selected version as `version_stage="final"`.
- Previous final version(s) are cleared back to draft.
- Project final pointer is written to `projects.final_version_number`.

Variant label carry-forward:
- If editorial source is `variant` or `editorial`, `variant_label` is retained.
- If source is `base`, `variant_label` remains `null`.

## 5. Contracts and Validation

Primary contract file:
- `backend/src/contracts/prd.py`

Node-level request/response schemas:
- `backend/src/schemas/workflow.py`

Node contracts used by team boundaries:
- Node 0: `TopicInitializationRequest/Response`
- Node 1: `ResearchTrendResponse`
- Node 2: `MasterContentResponse` + `MasterContentVariant`
- Node 3: `EditorialRequest/Response`

Node 0 context bundle fields (current):
- `topic_title`
- `normalized_topic`
- `core_idea`
- `user_content`
- `target_audience`:
  - `primary_segment` (required)
  - `notes` (optional)
- `audience_familiarity`
- `detail_level`
- `tone_preference`
- `stance`
- `primary_goal`
- `desired_action`
- `voice_profile_id` (required placeholder field)
- `constraints`
- `distribution_targets` (optional planning field)

## 6. Orchestration Notes

Key orchestrator:
- `backend/src/services/orchestration/engine.py`

Responsibilities:
- executes node sequence
- persists content versions and metadata
- persists project final pointer
- generates artifacts (on-demand endpoint and selected editorial finalize paths)
- regenerates adapter outputs on editorial finalize paths that run the post-editorial pipeline

## 7. React UI

Primary UI files:
- `ui/react/src/App.jsx`
- `ui/react/src/styles.css`
- `ui/react/README.md`

The UI supports:
- node-by-node run with audit panel (Node 0 -> Node 1 -> Node 2)
- non-blocking inline progress bar for long-running calls
- version selection and in-place keyword patching
- direct finalize selected version
- inline edit/save/finalize flow
- iterate preview/save/finalize flow
- save-time version naming (prompt on save click)
- artifact generation by kind/format multi-select
- kind-scoped + format-scoped artifact style settings (`style_settings_by_kind`, `style_settings_by_format`)
- generated artifact view as per-artifact tabs
- stored artifact retrieval view (shown as a separate artifacts sub-view)
- inline artifact title rename in stored artifacts view
- Publish stage with dynamic platform list + adapter field mapping UI (`Publish` button intentionally disabled until adapter publish implementation is finalized)

## 8. Important Operational Notes

- Startup now relies on SQLAlchemy model metadata only (`create_all()`); legacy compatibility patching has been removed.
- Full integration tests are currently Postgres/.env-dependent by design.
- `backend/.env` contains secrets and is now ignored by `.gitignore`; do not commit real credentials.
