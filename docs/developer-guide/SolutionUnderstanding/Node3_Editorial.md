# Node 3 Editorial

Node 3 supports editing, previewing, saving, and finalizing content versions.

## Runtime Surface

| Purpose | Endpoint |
|---------|----------|
| Single-pass edit and finalize | `POST /api/v1/workflows/nodes/editorial` |
| Start session | `POST /api/v1/workflows/nodes/editorial/session/start` |
| Iterate session | `POST /api/v1/workflows/nodes/editorial/session/{session_id}/iterate` |
| Finalize session | `POST /api/v1/workflows/nodes/editorial/session/{session_id}/finalize` |
| Regenerate against outline | `POST /api/v1/workflows/nodes/editorial/regenerate-outline` |
| Save inline draft | `POST /api/v1/workflows/nodes/editorial/save-inline` |
| Preview feedback | `POST /api/v1/workflows/nodes/editorial/feedback/preview` |
| Finalize existing version | `POST /api/v1/workflows/nodes/editorial/finalize-selected` |
| Patch version keywords | `PATCH /api/v1/versions/{project_id}/{version_number}/keywords` |

Main implementation:

- `backend/src/services/orchestration/nodes/editorial.py`
- `backend/src/services/orchestration/engine.py`
- `backend/src/api/v1/endpoints/workflows.py`
- `backend/src/api/v1/endpoints/versions.py`
- `backend/src/schemas/workflow.py`

## Version Semantics

Editorial-created rows are stored in `content_versions`:

| Operation | Version behavior |
|-----------|------------------|
| Regenerate outline | Creates `version_kind="editorial"`, `version_stage="draft"` |
| Save inline | Creates `version_kind="editorial"`, `version_stage="draft"` |
| Session finalize | Creates finalized editorial version |
| Direct editorial finalize | Creates finalized editorial version |
| Finalize selected | Marks an existing version final without creating a new row |
| Feedback preview | No persistence |

On finalization:

- Existing final versions for the project are reset to draft.
- The selected/new version is marked `version_stage="final"`.
- `projects.final_version_number` and `projects.finalized_at` are updated.

## Variant Label Carry-Forward

| Source version kind | New editorial `variant_label` |
|---------------------|-------------------------------|
| `base` | `null` |
| `variant` | source `variant_label` |
| `editorial` | source `variant_label` |

`save-inline` can also accept `version_label`; when provided, it is saved as the new draft's `variant_label`.

## Contract Rules

Keep these stable unless the UI and downstream services are updated together:

- `EditorialRequest`
- `EditorialResponse`
- version response shapes
- `ContentVersionEntity`

## Implementation Rules

- Never leave more than one final version for a project.
- Preserve `source_version_number` when creating editorial versions.
- Do not auto-generate artifacts from `finalize-selected`; artifact generation is an explicit later step.
- Preview endpoints must not write content versions.
- Guard against empty or degenerate edited content.

## Test Checklist

- Finalize-selected updates the project pointer.
- Finalization resets previous final versions.
- Variant labels carry forward correctly through editorial chains.
- Feedback preview does not persist.
- Artifact generation can run after finalization.
