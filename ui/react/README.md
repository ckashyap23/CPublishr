# React UI (Current)

Voice-profile module UI for the current backend surface.

## What it covers

1. Auth
   - Signup: `user_id`, `email`, `password`
   - Login: `email`, `password`
   - Current user fetch: `GET /api/v1/auth/me`
2. Voice profile collections
   - Create collection with profile name + multi-platform selection
   - List collections for the logged-in user
   - Load collection detail with versions
3. Generate version from dataset inputs
   - Supports one or more datasets per generation request
   - Fields per dataset: `dataset_id` (optional), `dataset_name`, `source_profile` (optional), `blob_prefix`, `sample_scope_note` (optional)
4. Version controls
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
