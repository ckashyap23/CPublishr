# CPublishr

**Content Operating System** — take an idea from raw input to publish-ready, platform-native artifacts with consistent voice and tone.

Built with FastAPI + PostgreSQL (backend) and React (frontend). Self-hostable and open-source under the [MIT License](LICENSE).

## How It Works

1. **Initialize** a topic with your idea, target audience, tone, and optional voice profile
2. **Research** — Node 1 enriches the topic with structured context
3. **Master content** — Node 2 produces a long-form master draft
4. **Editorial** — Node 3 refines and finalizes the content interactively
5. **Artifacts** — Generate platform-specific formats (LinkedIn post, Instagram caption, etc.)
6. **Publish** — Push to platforms or download as a ZIP bundle

## Project Layout

```
backend/src/           -> FastAPI backend (API, services, models, adapters)
backend/pyproject.toml -> Backend dependency source of truth
ui/react/              -> React SPA (Vite)
docs/                  -> Architecture and team handoff docs
infra/docker/          -> docker-compose (Postgres, Redis, API)
backend/contracts/     -> Example request/response JSON contracts
```

## Prerequisites

- Python 3.11+
- Node.js 18+ / npm
- PostgreSQL (local or hosted)
- Azure OpenAI credentials (for LLM-powered nodes)

## Quick Start

See [DEVELOPMENT.md](DEVELOPMENT.md) for full cross-platform setup instructions.

```bash
# Backend (from backend/)
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env   # then edit DATABASE_URL and AUTH_JWT_SECRET
uvicorn src.main:app --reload --port 8010

# Frontend (from ui/react/)
npm install && npm run dev
```

On first startup with `DB_AUTO_CREATE=true` in `.env`, all tables are created automatically.

API docs (Swagger UI) available at `http://127.0.0.1:8010/docs`.

## API Overview (48 routes)

All protected endpoints require `Authorization: Bearer <token>`.

### Auth (`/api/v1/auth`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/signup` | Create account (`user_id`, `email`, `password`) |
| POST | `/login` | Get JWT token |
| GET | `/me` | Current user info |

### Projects (`/api/v1/projects`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List user projects |
| POST | `/` | Initialize topic / Node 0 |
| GET | `/{project_id}` | Get project detail |

### Workflow (`/api/v1/workflows`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/runs` | Run Nodes 0-2, returns `awaiting_editorial` |
| GET/POST | `/nodes/research/{project_id}` | Node 1 - Research |
| GET/POST | `/nodes/master/{project_id}` | Node 2 - Master content |
| POST | `/nodes/editorial` | Node 3 - Editorial |
| POST | `/nodes/editorial/session/start` | Start editorial session |
| POST | `/nodes/editorial/session/{id}/iterate` | Iterate session |
| POST | `/nodes/editorial/session/{id}/finalize` | Finalize session |
| POST | `/nodes/editorial/finalize-direct` | Finalize without session |
| POST | `/nodes/editorial/regenerate-outline` | Regenerate outline draft |
| POST | `/nodes/editorial/save-inline` | Save inline draft |
| POST | `/nodes/editorial/feedback/preview` | Preview with feedback |
| POST | `/nodes/editorial/finalize-selected` | Finalize a selected version |
| POST | `/nodes/artifacts/generate` | Generate artifacts from latest editorial |

### Artifacts (`/api/v1/artifacts`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/catalog/formats` | Dynamic format catalog |
| POST | `/generate` | On-demand artifact generation |
| POST | `/edit` | Edit existing artifact |
| POST | `/suggest` | Suggest artifact styles |
| GET | `/{project_id}` | List all artifacts |
| GET | `/{project_id}/{format}` | List by format |
| GET | `/{project_id}/kind/{kind}` | List by kind |
| PATCH | `/item/{artifact_id}/title` | Rename artifact |

### Versions (`/api/v1/versions`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{project_id}` | List all versions |
| GET | `/{project_id}/{version_kind}` | Filter by kind |
| PATCH | `/{project_id}/{version_number}/keywords` | Patch keywords |

### Platform Outputs (`/api/v1/platform-outputs`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{project_id}` | List platform outputs |

### Publishing (`/api/v1/publishing`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/platforms` | List available platforms |
| GET | `/platforms/{platform}/fields` | Platform field schema |
| POST | `/jobs` | Create publish job (legacy) |
| POST | `/jobs/artifacts` | Create artifact publish job |
| POST | `/save-to-publish` | Save bundle to path |
| POST | `/download-bundle` | Download bundle as ZIP |
| GET | `/output-path/browse` | Browse server-side directories |
| POST | `/output-path/pick-local` | Native folder picker (desktop only) |

### Voice Profiles (`/api/v1/voice-profiles`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/collections` | Create collection |
| GET | `/collections` | List collections |
| GET | `/collections/{id}` | Get collection |
| POST | `/collections/{id}/datasets` | Add dataset |
| POST | `/collections/{id}/profiles` | Create profile |
| GET | `/profiles` | List profiles |
| GET | `/profiles/{id}` | Get profile |
| POST | `/profiles/{id}/status` | Update profile status |
| DELETE | `/profiles/{id}` | Delete profile |
| POST | `/profiles/{id}/versions/generate` | Generate version |
| GET | `/versions/{id}` | Get version |
| POST | `/versions/{id}/activate` | Activate version |
| POST | `/versions/{id}/status` | Update version status |

## Data Model (14 tables)

| Table | Purpose |
|-------|---------|
| `users` | Auth accounts |
| `projects` | Topic context + final version pointer |
| `content_versions` | Base / variant / editorial versions |
| `editorial_sessions` | Working content during editorial |
| `artifacts` | Generated text / image / video / audio / gif / bundle |
| `platform_outputs` | Legacy per-platform formatted content |
| `publish_jobs` | Publish job records with payload snapshots |
| `user_context_memory` | UI state persistence per user |
| `voice_profile_collections` | Named voice profile containers |
| `voice_profiles` | Individual profiles within a collection |
| `voice_profile_datasets` | Dataset metadata (blob prefix, entry count) |
| `voice_profile_versions` | Generated voice profile versions |
| `voice_profile_version_datasets` | Dataset <-> version lineage |
| `dataset_entries` | Individual content entries with inferred labels |

## Platform Adapters

| Adapter | Status |
|---------|--------|
| LinkedIn | Schema + composition + save-to-publish |
| Instagram | Schema + composition + save-to-publish |

New adapters are auto-discovered via registry. See [docs/developer-guide/Generate_Adapter.md](docs/developer-guide/Generate_Adapter.md).

## DB Migrations (Alembic)

```bash
# macOS / Linux
cd backend && alembic upgrade head

# Windows
cd backend && .\.venv\Scripts\alembic.exe upgrade head
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for creating new migrations.

## Configuration

Key environment variables (see `backend/.env.example` for the full list):

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AUTH_JWT_SECRET` | Yes | Long random string — `openssl rand -hex 32` |
| `CORS_ALLOW_ORIGINS` | Production | Comma-separated allowed frontend origins |
| `AZURE_OPENAI_ENDPOINT` | LLM features | Azure OpenAI resource URL |
| `AZURE_OPENAI_SUBSCRIPTION_KEY` | LLM features | Azure OpenAI API key |
| `VITE_API_BASE_URL` | Frontend | Backend URL (set in `ui/react/.env`) |

## Design Principles

- Same idea, different platform-native packaging
- Voice consistency via user voice profiles
- Contract-first integration between workflow nodes
- All content is user-scoped via JWT auth

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

## References

- [docs/solution_understanding.md](docs/solution_understanding.md) - architecture overview
- [docs/developer-guide/](docs/developer-guide/) - team handoff guides per module
- [ui/react/README.md](ui/react/README.md) - React UI setup
