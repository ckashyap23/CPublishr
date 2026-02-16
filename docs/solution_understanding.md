# Solution Understanding

This document explains how the current backend works end-to-end, based on the live code in this repository.

## 1. Product Scope (Current MVP)

The system supports a contract-first content workflow:
1. Node 0: Topic initialization
2. Node 1: Research synthesis
3. Node 2: Master content generation (base + optional variants)
4. Node 3: Editorial refinement
5. Platform adaptation and publish-stub testing

Design intent in current code:
- Keep component contracts strict and testable.
- Keep endpoints separately testable.
- Allow asynchronous team work by stabilizing node boundaries.

## 2. Runtime Architecture

Backend stack:
- Python + FastAPI
- SQLAlchemy ORM
- Postgres via `DATABASE_URL`
- Optional Azure OpenAI for Node logic and editorial refinement

Entry point:
- `backend/src/main.py`

Startup behavior:
- Loads settings from `.env`.
- Registers v1 API router.
- Runs `create_all()` on startup when `DB_AUTO_CREATE=true`.

Important:
- `create_all()` creates missing tables but does not alter existing columns.
- Schema changes still require SQL migration/ALTER for existing DBs.

## 3. API Surface (v1)

Router:
- `backend/src/api/v1/router.py`

Endpoints:
- `POST /api/v1/projects/`: Run Node 0, clear prior project-scoped data for the same `project_id`, and persist fresh context bundle.
- `GET /api/v1/projects/{project_id}`: Fetch project metadata.
- `POST /api/v1/workflows/runs`: Run default flow (Node 0->1->2 + adapters), optionally auto-run editorial.
- `GET /api/v1/workflows/nodes/research/{project_id}`: Run Node 1 independently.
- `POST /api/v1/workflows/nodes/research`: Run Node 1 from explicit payload (no full workflow run required).
- `GET /api/v1/workflows/nodes/master/{project_id}`: Run Node 2 independently and persist base + variants.
- `POST /api/v1/workflows/nodes/master`: Run Node 2 from explicit payload; optional research injection.
- `POST /api/v1/workflows/nodes/editorial`: Single-pass editorial.
- `POST /api/v1/workflows/nodes/editorial/session/start`: Start iterative editorial session.
- `POST /api/v1/workflows/nodes/editorial/session/{session_id}/iterate`: Iterate session draft.
- `POST /api/v1/workflows/nodes/editorial/session/{session_id}/finalize`: Finalize session to new content version.
- `GET /api/v1/versions/{project_id}`: List versions with metadata.
- `GET /api/v1/versions/{project_id}/{version_kind}`: List versions for one kind (`base`, `variant`, `editorial`).
- `GET /api/v1/platform-outputs/{project_id}`: List adapter outputs.
- `POST /api/v1/publishing/jobs`: Publish stub (validated internal payload path).
- `GET /healthz`, `GET /api/v1/health/`: Health checks.

## 4. Contract-First Model

Source of truth:
- `backend/src/contracts/prd.py`

Validation examples:
- `backend/contracts/examples/*.json`

Contract tests:
- `backend/tests/unit/test_prd_contract_examples.py`
- `backend/tests/unit/test_context_bundle_schema.py`

### Key active contracts

Node 0 request (`TopicInitializationRequest`):
- Required: `project_id`, `topic_title`, `core_idea`, `tone_preference`, `distribution_targets`
- Optional: `user_content`, `target_audience`, `content_depth`

Node 1 response (`ResearchTrendResponse`):
- `research_summary`, `emerging_tools`, `recent_discussions`, `key_insights`, `contrarian_angles`

Node 2 response (`MasterContentResponse`):
- `master_document`
- `structure_outline` (section map semantics)
- `core_arguments`
- Optional `master_variants[]` where each variant includes:
  - `label`
  - `master_document`
  - `structure_outline`
  - `core_arguments`

Node 3 response (`EditorialResponse`):
- `draft_version`, `updated_master_document`, `change_log`

Version entity (`ContentVersionEntity`):
- `version_id`, `project_id`, `version_number`, `content`
- Optional metadata fields:
  - `version_kind` (`base | variant | editorial`)
  - `variant_label`

## 5. Node-by-Node Behavior

### Node 0 (`topic_initialization.py`)
- Normalizes topic title (optionally via LLM).
- Builds canonical `context_bundle`.
- Validates against `ContextBundleV1` schema.
- Marks a fresh run boundary for the project by clearing prior project-scoped rows:
  - `content_versions`
  - `platform_outputs`
  - `publish_jobs`
  - `editorial_sessions`
  - existing `projects` row (recreated during init)
- Persists into project `context_json`.

### Node 1 (`research_trends.py`)
- Reads `context_bundle` from state.
- Produces structured research payload.
- Uses fallback deterministic output if LLM unavailable/fails.
- Stores result in `context.state["research"]`.

### Node 2 (`master_content.py`)
- Reads `context_bundle` + `research`.
- Produces base master document and optional variants.
- Ensures `structure_outline` is section-map semantics for base and variants.
- Returns strict contract-compatible output.

### Node 3 (`editorial.py` + engine session methods)
- Edits selected version content.
- Supports both single-pass and iterative session workflows.
- Uses global `next_version_number` when persisting editorial output.
- Persisted editorial rows are marked `version_kind="editorial"`.

## 6. Orchestration and Persistence

Engine:
- `backend/src/services/orchestration/engine.py`

Default run (`run_default_flow`):
1. Node 0 -> persist `context_bundle` to project
2. Node 1
3. Node 2
4. Persist base content version
5. Persist each variant as separate content version
6. Run adapters for distribution targets
7. Persist adapter outputs

Editorial targeting in workflow run:
- `POST /workflows/runs` with `run_editorial=true` selects latest `base` version first.
- Falls back to latest overall version if no base exists.

## 7. Database Model (Current)

Tables:
- `projects`
  - includes `context_json` for persisted Node 0 bundle
- `content_versions`
  - includes `version_kind` and `variant_label`
- `platform_outputs`
- `publish_jobs`
- `editorial_sessions`

Current persistence semantics:
- Base master content -> `content_versions` (`version_kind="base"`)
- Variant master content -> `content_versions` (`version_kind="variant"`, with `variant_label`)
- Editorial outputs -> `content_versions` (`version_kind="editorial"`)

## 8. Adapter and Publishing Path

Adapters:
- `backend/src/services/platforms/adapters/*`
- Input: base master document + context
- Output: contract-compliant per-platform payloads
- Persisted in `platform_outputs` as JSON string

Publishing:
- Current implementation is a validated publish stub.
- Creates `publish_jobs` only if matching platform output exists.
- Returns `DistributionResponse` with stub external id.

## 9. Testing Strategy

Unit:
- Contract example validation
- Context bundle schema validation
- Health endpoint checks

Integration:
- Full happy-path flow
- MVP end-to-end flow
- Editorial version-selection behavior:
  - workflow auto-editorial chooses base first
  - editorial persists with global next version number

## 10. UI for Manual Backend Testing

Streamlit tester:
- `ui/streamlit/app.py`

Capabilities:
- Curl-aligned flow from health -> node runs -> storage -> publish
- Separate API console
- Request/response visibility for manual debugging

Backend URL is configurable in sidebar (default currently points to `127.0.0.1:8010` in code).

## 11. Team Collaboration Boundaries

Recommended ownership model:
- Node 0/contract boundary: context schema stability
- Node 1: research internals, fixed output shape
- Node 2: content quality and variant generation, fixed response contract
- Node 3: editorial quality/session behavior, fixed editorial contracts
- Adapters: platform transformation logic, fixed adapter contracts

Rule of thumb:
- Change internals freely.
- Change external contracts only with coordinated update to:
  1. `prd.py`
  2. example JSON files
  3. contract tests
  4. relevant handoff docs

## 12. Known Operational Notes

- Existing DBs must be altered manually for new columns (`create_all()` does not mutate existing schema).
- FastAPI startup event currently uses `on_event("startup")` (deprecation warning is known, not blocking).
- Streamlit and backend can run on different ports; base URL in UI must match active backend port.
