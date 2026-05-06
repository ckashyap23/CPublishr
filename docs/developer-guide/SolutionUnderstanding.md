# CPublishr Solution Overview

Start here when you are new to the repository. This document explains the current product shape, the main runtime flow, and where to go for implementation details.

## What CPublishr Does

CPublishr turns one content idea into publish-ready, platform-aware assets:

1. Create a project from topic, audience, goal, tone, and optional voice profile.
2. Run research to enrich the topic.
3. Generate master content and optional variants.
4. Edit, save, and finalize the preferred content version.
5. Generate text, image, video, or GIF artifacts from finalized content.
6. Map artifacts into platform-specific publish bundles through adapters.

The app is a FastAPI backend, PostgreSQL-compatible database, and React/Vite frontend.

## System Map

| Area | Main files | Details |
|------|------------|---------|
| Local setup and deployment | `docs/developer-guide/Development.md`, `render.yaml`, `backend/.env.example` | [Development Guide](Development.md) |
| Workflow orchestration | `backend/src/services/orchestration/engine.py` | Node docs below |
| Node 1 research | `backend/src/services/orchestration/nodes/research_trends.py` | [Node 1 Research](SolutionUnderstanding/Node1_Research.md) |
| Node 2 master content | `backend/src/services/orchestration/nodes/master_content.py` | [Node 2 Master Content](SolutionUnderstanding/Node2_MasterContent.md) |
| Node 3 editorial | `backend/src/services/orchestration/nodes/editorial.py` | [Node 3 Editorial](SolutionUnderstanding/Node3_Editorial.md) |
| Artifact generation | `backend/src/services/orchestration/artifacts/` | [Generate Artifacts](SolutionUnderstanding/Generate_Artifacts.md) |
| Publishing flow | `backend/src/services/publishing/service.py` | [Publishing](SolutionUnderstanding/Publishing.md) |
| New platform adapters | `backend/src/platforms/adapters/` | [Generate Adapter](SolutionUnderstanding/Generate_Adapter.md) |
| Voice profiles | `backend/src/services/voice_profiles/` | [Voice Profiles](Voice_Profile.md) |
| React app | `ui/react/src/App.jsx`, `ui/react/src/components/`, `ui/react/src/lib/` | `ui/react/README.md` |

## Backend Flow

The primary workflow is:

1. `POST /api/v1/projects/`
   Creates a project and stores the Node 0 context bundle.
2. `POST /api/v1/workflows/runs`
   Runs Node 1 and Node 2, then returns `status="awaiting_editorial"`.
3. Editorial endpoints
   Save drafts, preview feedback, or finalize a selected version.
4. `POST /api/v1/artifacts/generate`
   Generates artifacts from finalized content using the dynamic artifact catalog.
5. Publishing endpoints
   Map generated artifacts into adapter-defined platform fields and save or publish bundles.

`POST /api/v1/workflows/runs` does not auto-finalize editorial content. Artifact generation is intentionally explicit.

## Core API Groups

| Group | Routes |
|-------|--------|
| Health | `GET /healthz`, `GET /api/v1/health/` |
| Auth | `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me` |
| Projects | `GET/POST /api/v1/projects/`, `GET /api/v1/projects/{project_id}` |
| Workflow | `/api/v1/workflows/runs`, `/api/v1/workflows/nodes/*` |
| Versions | `/api/v1/versions/{project_id}` |
| Artifacts | `/api/v1/artifacts/*` |
| Publishing | `/api/v1/publishing/*` |
| Voice profiles | `/api/v1/voice-profiles/*` |

Protected API routes require `Authorization: Bearer <token>`.

## Data Model

Key tables:

| Table | Purpose |
|-------|---------|
| `users` | Auth accounts |
| `projects` | Project context and final version pointer |
| `content_versions` | Base, variant, and editorial versions |
| `editorial_sessions` | Temporary editorial working state |
| `artifacts` | Generated text/media/bundle artifacts |
| `platform_outputs` | Legacy platform output records |
| `publish_jobs` | Publish/save job records and payload snapshots |
| `voice_profile_*` | Voice profile collections, datasets, generated versions, and lineage |
| `dataset_entries` | Individual voice profile source entries |

SQLAlchemy models live in `backend/src/db/models/`. Repository classes live in `backend/src/db/repositories/`.

## Contracts

Keep public contracts stable unless the frontend and downstream services are updated together.

| Contract area | File |
|---------------|------|
| Core workflow contracts | `backend/src/contracts/prd.py` |
| Workflow request/response schemas | `backend/src/schemas/workflow.py` |
| Publishing schemas | `backend/src/schemas/publishing_schemas.py` |
| Artifact contracts | `backend/src/services/orchestration/artifacts/contracts.py` |

## Configuration

Required for normal development:

- `DATABASE_URL`
- `AUTH_JWT_SECRET`

Text LLM providers:

- Azure OpenAI: `LLM_PROVIDER=azure`
- Standard OpenAI: `LLM_PROVIDER=openai`

Media generation and cloud storage are optional. If Azure image, video, or Blob settings are empty, the core text workflow can still run with the configured database and text LLM provider.

See [Development Guide](Development.md) for exact setup commands and provider-specific environment variables.

## Extension Paths

Use these guides when changing a specific part of the system:

- Add a platform adapter: [Generate Adapter](SolutionUnderstanding/Generate_Adapter.md)
- Add or change artifact formats: [Generate Artifacts](SolutionUnderstanding/Generate_Artifacts.md)
- Change research behavior: [Node 1 Research](SolutionUnderstanding/Node1_Research.md)
- Change master content generation: [Node 2 Master Content](SolutionUnderstanding/Node2_MasterContent.md)
- Change editorial/versioning behavior: [Node 3 Editorial](SolutionUnderstanding/Node3_Editorial.md)
- Change publish mapping or save-to-publish: [Publishing](SolutionUnderstanding/Publishing.md)
- Change voice profile behavior: [Voice Profiles](Voice_Profile.md)

## Operational Notes

- `backend/.env` must never be committed.
- Integration tests currently assume a Postgres-compatible `DATABASE_URL`.
- Adapter and artifact registries discover modules at backend startup; restart after adding files.
- `VITE_API_BASE_URL` is baked into the React production build.
