# Voice Profile Module - Team Handoff Guide

This document explains the current voice profile implementation (as built)

## Goal

Enable each authenticated user to:
- Create named voice profile collections (with multiple platforms)
- Generate versioned voice profiles from one or more blob-backed datasets
- Persist full generated profile JSON + structured fields
- Track dataset lineage per generated version
- Activate one version for downstream use

## Current API Surface

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/voice-profiles/collections` | Create collection |
| GET | `/api/v1/voice-profiles/collections` | List collections |
| GET | `/api/v1/voice-profiles/collections/{id}` | Get collection detail |
| POST | `/api/v1/voice-profiles/collections/{id}/datasets` | Add dataset |
| POST | `/api/v1/voice-profiles/collections/{id}/profiles` | Create profile |
| GET | `/api/v1/voice-profiles/profiles` | List profiles |
| GET | `/api/v1/voice-profiles/profiles/{id}` | Get profile |
| POST | `/api/v1/voice-profiles/profiles/{id}/status` | Enable/disable profile |
| DELETE | `/api/v1/voice-profiles/profiles/{id}` | Delete profile |
| POST | `/api/v1/voice-profiles/profiles/{id}/versions/generate` | Generate new version |
| GET | `/api/v1/voice-profiles/versions/{id}` | Get version detail |
| POST | `/api/v1/voice-profiles/versions/{id}/activate` | Activate version |
| POST | `/api/v1/voice-profiles/versions/{id}/status` | Update version status |

Router source: `backend/src/api/v1/router.py`

## Data Model (Current)

DB bootstrap currently creates only:
- `users`
- `voice_profile_collections`
- `voice_profile_versions`
- `voice_profile_version_datasets`
- `dataset_entries`

Definition sources:
- `backend/src/db/models/user.py`
- `backend/src/db/models/voice_profile_collection.py`
- `backend/src/db/models/voice_profile_version.py`
- `backend/src/db/models/voice_profile_version_dataset.py`
- `backend/src/db/models/dataset_entry.py`
- `backend/src/db/init_db.py`

Important implementation details:
- `users.user_id` is `varchar(64)` (not UUID) and is the auth identity.
- `voice_profile_collections.user_id` references `users.user_id`.
- `voice_profile_collections.platforms` is `jsonb` array (multi-platform per collection).
- `voice_profile_versions` has unique `(voice_profile_id, version_no)`.
- `voice_profile_version_datasets` has unique `(voice_profile_version_id, dataset_id)`.
- `dataset_entries.entry_type` is checked against allowed enum values.

## End-to-End Backend Flow

### 1) Signup/Login

- Signup requires: `user_id`, `email`, `password`.
- Login requires: `user_id`, `password`.
- Signup creates one row in `users` and returns bearer token.

Code:
- `backend/src/api/v1/endpoints/auth.py`
- `backend/src/db/repositories/user_repository.py`

### 2) Create Voice Profile Collection

Request:
- `voice_profile_name` (required)
- `platforms` (required list, min 1)

Behavior:
- Creates one row in `voice_profile_collections`.
- Automatically creates initial version row in `voice_profile_versions` with:
  - `version_no=1`
  - `is_active=false`
  - `generation_status="draft"`
  - empty structured payload fields

Code:
- `backend/src/api/v1/endpoints/voice_profiles.py`
- `backend/src/services/voice_profiles/service.py`
- `backend/src/db/repositories/voice_profile_module_repository.py`

### 3) Generate New Version (Datasets + LLM)

Request:
- `intended_use` (optional)
- `datasets[]` (min 1), each with:
  - `dataset_id` (optional)
  - `dataset_name` (required)
  - `source_profile` (optional)
  - `blob_prefix` (required)
  - `sample_scope_note` (optional)

Behavior:
1. Ingest blobs from configured Azure container using `blob_prefix`.
2. Upsert `dataset_entries` for found blobs.
3. Build generation payload from ingested entries.
4. Generate profile JSON with Azure OpenAI client (or fallback template if LLM disabled).
5. Create a new `voice_profile_versions` row with incremented `version_no`.
6. Upsert lineage rows in `voice_profile_version_datasets` for each dataset.

Code:
- `backend/src/services/voice_profiles/service.py`
- `backend/src/services/llm/azure_openai.py`
- `backend/src/db/repositories/voice_profile_module_repository.py`

### 4) Approve/Activate/Status

- Activate endpoint sets selected version active and marks status approved.
- Status endpoint supports: `draft`, `generated`, `approved`, `rejected`, `failed`.

Code:
- `backend/src/api/v1/endpoints/voice_profiles.py`
- `backend/src/db/repositories/voice_profile_module_repository.py`

## Azure Blob Contract

Config keys:
- `AZURE_STORAGE_CONNECTION_STRING` -> `azure_storage_connection_string`
- `AZURE_PROFILE_ENTRIES_CONTAINER` -> `azure_profile_entries_container` (default `profile-entries`)

Recommended blob path pattern:
- `<user_id>/<dataset_name>/<files...>`

The API accepts arbitrary `blob_prefix`, so caller controls dataset scope per generation request.

## UI Coverage (Current)

React app supports:
- Signup/Login/Logout
- Collection create/list/select
- Generate version with one or more dataset input rows
- Version detail view (raw + structured fields + lineage)
- Activate version
- Update generation status

UI source:
- `ui/react/src/App.jsx`

## Notes: Spec vs Current Implementation

Implemented from spec:
- User-scoped collections and versions
- Multi-platform collection model
- Dataset ingestion from blob
- Generated version persistence
- Dataset lineage tracking
- Activation flow

Current simplifications:
- Preprocess and generate logic are consolidated in one service (`voice_profiles/service.py`) rather than two physical scripts.
- `dataset_entries` enrichment fields (`format_family`, `hook_type`, `cta_type`, `theme_tags`) are not fully LLM-enriched yet; initial ingestion writes conservative defaults.
- `platforms` is currently required at collection create time.

## Operational Notes

- If DB tables are cleared, startup recreates the target schema when `db_auto_create=true`.
- No users exist after reset until signup is called.
- First signup inserts first row into `users`.

## File Map (Primary)

- API:
  - `backend/src/api/v1/endpoints/auth.py`
  - `backend/src/api/v1/endpoints/voice_profiles.py`
  - `backend/src/api/v1/router.py`
- Services:
  - `backend/src/services/voice_profiles/service.py`
  - `backend/src/services/llm/azure_openai.py`
- Persistence:
  - `backend/src/db/repositories/user_repository.py`
  - `backend/src/db/repositories/voice_profile_module_repository.py`
  - `backend/src/db/models/*` (voice profile module tables)
  - `backend/src/db/init_db.py`
- UI:
  - `ui/react/src/App.jsx`
