# React UI (Current)

Current UI for project workflow (Node 0-3/editorial), artifacts, and voice-profile modules.

## What it covers

1. Auth
   - Signup: `user_id`, `email`, `password`
   - Login: `user_id`, `password`
   - Current user fetch: `GET /api/v1/auth/me`
2. Project workflow + editorial
   - Project ID field with user-scoped project suggestions (`GET /api/v1/projects/`)
   - Node 0 -> Node 2 generation flow
   - Editorial version selection, inline save, preview, finalize
   - Retrieve content when versions already exist for selected project
3. Artifacts
   - Dynamic artifact format catalog (`GET /api/v1/artifacts/catalog/formats`)
   - Multi-select artifact generation (`POST /api/v1/artifacts/generate`)
   - Kind-scoped + per-format style settings (`style_settings_by_kind`, `style_settings_by_format`)
   - Image style fields: theme, subject, avoid, medium, texture, lighting (12 options), palette mode, mood, composition, output fidelity
   - Video style fields: theme, subject, avoid, mood, lighting, palette mode, output fidelity, camera motion (format default or user override), energy level (low/medium/high)
   - Stored artifacts view (`GET /api/v1/artifacts/{project_id}`)
   - Inline artifact rename in stored view (`PATCH /api/v1/artifacts/item/{artifact_id}/title`)
4. Publish (artifact-mapped)
   - Dynamic platform list from adapter registry (`GET /api/v1/publishing/platforms`)
   - Dynamic platform field schema (`GET /api/v1/publishing/platforms/{platform}/fields`)
   - Source-level artifact mapping UI (`artifact_id + part + render_as`)
   - Publish button intentionally disabled until adapter publish API steps are implemented
5. Voice profile collections
   - Create collection with profile name + multi-platform selection
   - List collections for the logged-in user
   - Load collection detail with versions
6. Generate version from dataset inputs
   - Supports one or more datasets per generation request
   - Fields per dataset: `dataset_id` (optional), `dataset_name`, `source_profile` (optional), `blob_prefix`, `sample_scope_note` (optional)
7. Voice profile version controls
   - View generated version detail payloads
   - Activate selected version
   - Update status (`draft/generated/approved/rejected/failed`)

## Run

```powershell
cd C:\Cursor_Github\CPublishr\ui\react
npm install
npm run dev
```

or

```powershell
cd C:\Cursor_Github\CPublishr
.\ui\react\run.ps1 -Port 3000
```

Open:
- `http://127.0.0.1:3000`

Set backend URL in UI (default is `http://127.0.0.1:8010`).

## UI Notes

- Header title is `Publishr`.
- Artifacts page uses separate sub-views for generated vs stored artifacts (clicking `View Stored Artifacts` hides the generated panel).
- Workflow tabs now include `Publish` (Setup / Editorial / Artifacts / Publish).

---

## Backend Update Reference

Backend-side implemented changes (UI excluded) are tracked in [../../BACKEND_CHANGES.md](../../BACKEND_CHANGES.md).
