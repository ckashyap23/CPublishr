# Development Guide

Everything you need to run CPublishr locally on macOS, Linux, or Windows.

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | bundled with Node |
| PostgreSQL | 14+ | local or hosted (e.g. Neon, Supabase, Azure) |

---

## Backend Setup

```bash
# 1. Create and activate a virtual environment
cd backend

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies (editable mode)
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL and AUTH_JWT_SECRET
```

### Required `.env` values

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AUTH_JWT_SECRET` | Yes | Random string used to sign JWT tokens — run `openssl rand -hex 32` |
| `AZURE_OPENAI_ENDPOINT` | For LLM nodes | Azure OpenAI resource URL |
| `AZURE_OPENAI_SUBSCRIPTION_KEY` | For LLM nodes | Azure OpenAI API key |
| `CORS_ALLOW_ORIGINS` | Production | Comma-separated list of allowed frontend origins |

### Start the backend

```bash
# From the backend/ directory with .venv active
uvicorn src.main:app --reload --port 8010
```

API docs available at `http://127.0.0.1:8010/docs` once running.

### Database setup

With `DB_AUTO_CREATE=true` in `.env`, tables are created automatically on first startup.

To run Alembic migrations manually:

```bash
# macOS / Linux
alembic upgrade head

# Windows
.\.venv\Scripts\alembic.exe upgrade head
```

To create a new migration after changing a model:

```bash
# macOS / Linux
alembic revision --autogenerate -m "describe_your_change"

# Windows
.\.venv\Scripts\alembic.exe revision --autogenerate -m "describe_your_change"
```

---

## Frontend Setup

```bash
cd ui/react

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# VITE_API_BASE_URL defaults to http://127.0.0.1:8010 — no change needed for local dev

# Start dev server
npm run dev
```

The UI will be available at `http://localhost:5173`.

---

## Docker (optional)

A `docker-compose.yml` is provided in `infra/docker/` if you prefer to run Postgres and Redis via Docker:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

---

## Linting

```bash
# Python (from backend/)
ruff check src/

# Auto-fix where possible
ruff check src/ --fix
```

---

## Running Tests

```bash
# From backend/ with .venv active
pytest
```

---

## Project Structure

```
backend/
  src/
    api/v1/endpoints/   REST endpoints (one file per resource)
    core/               Config, security, logging
    db/
      models/           SQLAlchemy ORM models
      repositories/     Data access layer
    schemas/            Pydantic request/response schemas
    services/
      orchestration/    Workflow engine and nodes
      publishing/       Platform publishing adapters
      voice_profiles/   Voice profile management
  migrations/           Alembic migration scripts

ui/react/
  src/
    App.jsx             Main application (React SPA)

docs/                   Architecture docs and team guides
infra/                  Docker and environment templates
```

---

## Deploying to Render

A `render.yaml` at the project root defines both services. Deploy steps:

### 1. Deploy the backend first

In the Render dashboard, set these environment variables on `cpublishr-backend`:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | PostgreSQL connection string |
| `AUTH_JWT_SECRET` | `openssl rand -hex 32` |
| `CORS_ALLOW_ORIGINS` | Your frontend Render URL, e.g. `https://cpublishr-frontend.onrender.com` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource URL |
| `AZURE_OPENAI_SUBSCRIPTION_KEY` | Azure OpenAI key |
| `AZURE_API_KEY` | Azure AI key (for Flux image generation) |
| `AZURE_IMAGE_ENDPOINT` | Flux endpoint URL |
| `AZURE_IMAGE_DEPLOYMENT` | e.g. `FLUX.2-pro` |

The start command in `render.yaml` uses `$PORT` which Render injects automatically.

### 2. Deploy the frontend

Set this environment variable on `cpublishr-frontend` **before the build runs**:

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | Your backend Render URL, e.g. `https://cpublishr-backend.onrender.com` |

`VITE_API_BASE_URL` is baked into the static bundle at build time — if it's not set before the build, the frontend won't be able to reach the backend.

### Local vs production routing

| Environment | How `/api` calls are routed |
|-------------|----------------------------|
| Local dev (`npm run dev`) | Vite proxy → `http://127.0.0.1:8010` |
| Production (Render static site) | Direct fetch to `VITE_API_BASE_URL` |
