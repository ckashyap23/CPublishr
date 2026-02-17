# CPublishr

MVP for multi-node content orchestration with mandatory editorial finalization before artifacts/adapter outputs are used downstream.

## Project Layout

- Backend API: `backend/src`
- Backend dependency source of truth: `backend/pyproject.toml`
- React UI (active): `ui/react`
- Contracts + examples: `backend/src/contracts`, `backend/contracts/examples`
- Docs: `docs/`
- Local infra: `infra/docker/docker-compose.yml`

## Current Flow

1. Initialize topic context: `POST /api/v1/projects/`
2. Run Node 0-2 workflow: `POST /api/v1/workflows/runs` -> returns `awaiting_editorial`
3. Editorial workspace:
   - select any version
   - edit inline and save as a named draft
   - iterate via feedback preview, then save as named draft
   - finalize selected version directly (without editing) or finalize after save
   - patch keywords on existing version in-place
4. Finalization triggers downstream artifact + adapter output generation.

## Node 0 Input Contract

Required:
- `project_id`
- `topic_title`
- `core_idea`
- `tone_preference`
- `distribution_targets`

Optional:
- `user_content`
- `target_audience`
- `content_depth`

## References

- `docs/solution_understanding.md`
- `ui/react/README.md`
