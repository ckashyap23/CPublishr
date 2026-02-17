# React UI (Current)

Lightweight React UI for end-to-end flow testing.

## What it covers

1. Node 0 initialization form with defaults.
2. Generate content flow (Node 0 -> Node 1 -> Node 2) via:
   - `POST /api/v1/projects/`
   - `POST /api/v1/workflows/runs`
3. Editorial workspace:
   - version selection
   - keyword patch
   - direct finalize selected version (no edit required)
   - inline edit + save named draft
   - inline edit + save named draft + finalize
   - feedback preview
   - save preview as named draft
   - save preview as named draft + finalize
   - save-time version name prompt (asked only when Save is clicked)
4. Generate content loader overlay during long-running workflow call.
5. Artifacts placeholder page with empty links.

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
