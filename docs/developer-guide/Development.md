# Development Guide

Use this guide to run CPublishr locally or deploy it with your own providers.

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |
| PostgreSQL-compatible database | 14+ |

## Backend Setup

```bash
cd backend

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
cp .env.example .env
```

Edit `backend/.env` before starting the API.

Required values:

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | PostgreSQL-compatible connection string |
| `AUTH_JWT_SECRET` | Long random signing secret |
| `CORS_ALLOW_ORIGINS` | Required in production |

Start the backend:

```bash
uvicorn src.main:app --reload --port 8010
```

API docs:

```text
http://127.0.0.1:8010/docs
```

## Database

Any reachable Postgres-compatible service can be used. Azure Postgres is not required.

Examples:

```bash
# Local Postgres or Docker
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cpublishr

# Hosted Postgres
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

If a provider gives a URL beginning with `postgres://`, change it to `postgresql+psycopg://`.

Automatic table creation is controlled by:

```bash
DB_AUTO_CREATE=true
```

Manual migrations:

```bash
cd backend
alembic upgrade head
```

Create a migration after model changes:

```bash
cd backend
alembic revision --autogenerate -m "describe_change"
```

Using MySQL, SQLite, MongoDB, DynamoDB, or another non-Postgres database requires code changes in models, migrations, repositories, and integration tests.

## LLM Provider

Text LLM calls use `backend/src/services/llm/client.py`.

Supported providers:

| Provider | Required settings |
|----------|-------------------|
| Azure OpenAI | `LLM_PROVIDER=azure`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_SUBSCRIPTION_KEY`, `AZURE_OPENAI_API_VERSION` |
| Standard OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` |

Standard OpenAI example:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
```

To add another LLM provider, extend `backend/src/core/config.py` and `backend/src/services/llm/client.py` while keeping the public `chat(...)` and `is_enabled()` functions stable.

## Optional Media And Storage

These features are optional:

| Feature | Settings |
|---------|----------|
| Image generation | `AZURE_IMAGE_ENDPOINT`, `AZURE_IMAGE_DEPLOYMENT`, `AZURE_API_KEY` |
| Video generation | `AZURE_VIDEO_ENDPOINT`, `AZURE_VIDEO_DEPLOYMENT_NAME`, `AZURE_API_KEY` |
| Azure artifact storage | `AZURE_ARTIFACTS_ENABLED`, `AZURE_STORAGE_CONNECTION_STRING` |
| Save-to-publish output | `OUTPUT_PATH` |

Leave media/storage settings empty when you only need the core text workflow.

## Frontend Setup

```bash
cd ui/react
npm install
cp .env.example .env
npm run dev
```

Local UI:

```text
http://localhost:5173
```

`VITE_API_BASE_URL` defaults to the local backend during dev. In production, set it before building the frontend.

## Docker

Run bundled infrastructure:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

## Lint And Test

Backend lint:

```bash
cd backend
ruff check src/
```

Backend tests:

```bash
cd backend
pytest
```

Integration tests expect a Postgres-compatible `DATABASE_URL`.

## Render Deployment

`render.yaml` defines a Python backend and static React frontend.

Backend environment:

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | Render Postgres or any external Postgres-compatible URL |
| `AUTH_JWT_SECRET` | Long random signing secret |
| `CORS_ALLOW_ORIGINS` | Frontend URL |
| `LLM_PROVIDER` | `azure` or `openai` |
| Provider-specific LLM keys | Azure OpenAI keys or standard OpenAI keys |

Frontend environment:

| Variable | Notes |
|----------|-------|
| `VITE_API_BASE_URL` | Deployed backend URL |

`VITE_API_BASE_URL` is baked into the static build, so set it before the frontend build runs.
