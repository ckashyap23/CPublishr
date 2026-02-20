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
2. Run Node 0-2:
   - compact path: `POST /api/v1/workflows/runs` -> returns `awaiting_editorial`
   - node-by-node path (used by current React audit UI):
     - `POST /api/v1/workflows/nodes/research`
     - `POST /api/v1/workflows/nodes/master`
3. Editorial workspace:
   - select any version
   - edit inline and save as a named draft
   - iterate via feedback preview, then save as named draft
   - finalize selected version directly (without editing) or finalize after save
   - patch keywords on existing version in-place
4. Finalize selected content version.
5. Artifact generator page:
   - choose formats by kind
   - generate selected artifacts
   - view stored artifacts

## Node 0 Input Contract

Required:
- `project_id`
- `topic_title`
- `core_idea`
- `tone_preference`
- `voice_profile_id`
- `target_audience.primary_segment`

Optional:
- `user_content`
- `target_audience.notes`
- `audience_familiarity` (`new | somewhat_familiar | very_familiar`)
- `detail_level` (`quick_take | practical | deep_dive`)
- `stance` (`neutral | supportive | contrarian | balanced`, default `balanced`)
- `primary_goal` (`educate | thought_leadership | promote | entertain | recruit | community | convert`)
- `desired_action` (`comment | share | follow | click | dm | subscribe | buy`)
- `constraints` (JSON object)
- `distribution_targets`

## References

- `docs/solution_understanding.md`
- `docs/teamwork/Generate_Artifacts.md`
- `ui/react/README.md`
