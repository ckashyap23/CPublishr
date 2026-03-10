# CPublishr

Backend + React UI for user-scoped content workflows, artifacts, and voice-profile generation.

## Project Layout

- Backend API: `backend/src`
- Backend dependency source of truth: `backend/pyproject.toml`
- React UI (active): `ui/react`
- Contracts + examples: `backend/src/contracts`, `backend/contracts/examples`
- Docs: `docs/`
- Local infra: `infra/docker/docker-compose.yml`

## Current Flow

Authentication (required first):
- `POST /api/v1/auth/signup` with `user_id`, `email`, `password`
- `POST /api/v1/auth/login` with `user_id`, `password`
- Use `Authorization: Bearer <token>` for all protected endpoints
- `GET /api/v1/auth/me` to fetch current user

Projects / workflow / artifacts (user-scoped):
- `GET /api/v1/projects/` (list projects for current user)
- `POST /api/v1/projects/` (initialize/reset Node 0 topic context)
- `GET /api/v1/projects/{project_id}`
- `GET /api/v1/versions/{project_id}`
- `POST /api/v1/artifacts/generate`
- `GET /api/v1/artifacts/{project_id}`
- `PATCH /api/v1/artifacts/item/{artifact_id}/title` (rename artifact title)

Publishing (artifact-mapped, adapter-driven):
- `GET /api/v1/publishing/platforms`
- `GET /api/v1/publishing/platforms/{platform}/fields`
- `POST /api/v1/publishing/jobs/artifacts`
- `POST /api/v1/publishing/jobs` (legacy stub path using stored platform outputs)

Voice profile module (user-scoped):
- `POST /api/v1/voice-profiles/collections`
- `GET /api/v1/voice-profiles/collections`
- `GET /api/v1/voice-profiles/collections/{voice_profile_id}`
- `POST /api/v1/voice-profiles/collections/{voice_profile_id}/versions/generate`
- `GET /api/v1/voice-profiles/versions/{voice_profile_version_id}`
- `POST /api/v1/voice-profiles/versions/{voice_profile_version_id}/activate`
- `POST /api/v1/voice-profiles/versions/{voice_profile_version_id}/status`

Workflow/editorial/artifacts routes are active in the current UI-backed build.
`Publish` workflow page is also available in the React UI (mapping UI enabled, publish action intentionally disabled until adapter publish implementation is completed).

## Fresh DB Behavior

If DB tables are cleared and backend starts with auto-create enabled:
- Startup recreates target tables.
- No users exist initially.
- First successful signup inserts one row into `users`.
- Voice profile collections/versions are user-owned and created only via voice-profile APIs.

## References

- `docs/solution_understanding.md`
- `docs/teamwork/Generate_Artifacts.md`
- `ui/react/README.md`

## DB Migrations (Alembic)

From `backend/`:

- `.\.venv\Scripts\alembic.exe upgrade head`
- `.\.venv\Scripts\alembic.exe revision -m "your_change_name"`

---

## Backend Update Reference

Backend-side implemented changes (UI excluded) are tracked in [./BACKEND_CHANGES.md](./BACKEND_CHANGES.md).
