# Streamlit UI (Backend Tester)

This is a small Streamlit app for manually testing the FastAPI backend endpoints.

## What you'll get

- A **Curl-aligned Test Flow** tab that matches the common manual test sequence:
  - `GET /healthz`
  - `POST /api/v1/projects/` (re-initializing the same `project_id` resets prior project-scoped data)
  - `POST /api/v1/workflows/nodes/research`
  - `POST /api/v1/workflows/nodes/master`
  - `POST /api/v1/workflows/runs`
  - Editorial session flow:
    - `POST /api/v1/workflows/nodes/editorial/session/start`
    - `POST /api/v1/workflows/nodes/editorial/session/{session_id}/iterate`
    - `POST /api/v1/workflows/nodes/editorial/session/{session_id}/finalize`
  - Verify outputs:
    - `GET /api/v1/versions/{project_id}`
    - `GET /api/v1/platform-outputs/{project_id}`
  - Publish stub:
    - `POST /api/v1/publishing/jobs`
- Every call can show **request details** (method / URL / headers / JSON body) plus a **PowerShell curl** snippet you can paste into a terminal.
- An **API Console** tab for ad-hoc GET/POST requests.

## Run (local)

1) Start the backend (in a separate terminal):

```powershell
cd C:\Cursor_Github\CPublishr\backend
. .\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

2) Start Streamlit:

```powershell
cd C:\Cursor_Github\CPublishr
.\ui\streamlit\run.ps1
```

3) In the Streamlit UI, set **Backend base URL** to:
- whatever port you started uvicorn on (example: `http://127.0.0.1:8000` or `http://127.0.0.1:8010`)


