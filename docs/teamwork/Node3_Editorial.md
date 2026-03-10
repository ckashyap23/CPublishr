# Node3 Editorial - Team Handoff Guide

This document reflects the current editorial implementation and safe change boundaries.

## Goal

Support selection, iteration, and finalization of any content version (base, variant, or editorial) while preserving contracts and persistence semantics.

## Endpoint Surface

Core editorial:
- `POST /api/v1/workflows/nodes/editorial`
- `POST /api/v1/workflows/nodes/editorial/finalize-direct`

Session workflow:
- `POST /api/v1/workflows/nodes/editorial/session/start`
- `POST /api/v1/workflows/nodes/editorial/session/{session_id}/iterate`
- `POST /api/v1/workflows/nodes/editorial/session/{session_id}/finalize`

Explicit MVP editorial controls:
- `POST /api/v1/workflows/nodes/editorial/regenerate-outline`
- `POST /api/v1/workflows/nodes/editorial/save-inline`
- `POST /api/v1/workflows/nodes/editorial/feedback/preview`
- `POST /api/v1/workflows/nodes/editorial/finalize-selected`

Keyword editing (no new version):
- `PATCH /api/v1/versions/{project_id}/{version_number}/keywords`

## Current Data Semantics

Every editorial-created row is stored in `content_versions` with:
- `version_kind="editorial"`
- `version_stage`:
  - `draft` for regenerate/save-inline
  - `final` for finalize operations
- `source_version_number` from the version being edited
- `variant_label` carry-forward rules:
  - source kind `base` -> `variant_label=None`
  - source kind `variant` or `editorial` -> carry source `variant_label`

Project final pointer:
- On finalization, `projects.final_version_number` and `projects.finalized_at` are updated.
- Existing final version(s) are reset to draft before marking the new final.

## What Each Endpoint Does

`/nodes/editorial`:
- single-pass edit + persist finalized editorial version.

`/nodes/editorial/session/*`:
- stores temporary working content in `editorial_sessions`.
- finalization writes one finalized editorial version.

`/nodes/editorial/regenerate-outline`:
- LLM-guided rewrite against provided section outline.
- persists a new editorial draft version.

`/nodes/editorial/save-inline`:
- persists user-edited content as a new editorial draft version.
- accepts optional `version_label` and persists it as `variant_label` on the created editorial draft.

`/nodes/editorial/feedback/preview`:
- LLM preview only.
- no version persistence.

`/nodes/editorial/finalize-selected`:
- marks selected existing version as final (no new version row).
- does not auto-run artifact/adapters; generation continues via artifact generator flow.

## Files You Can Safely Change

Primary:
- `backend/src/services/orchestration/nodes/editorial.py`
- `backend/src/services/orchestration/engine.py`

Session persistence:
- `backend/src/db/models/editorial_session.py`
- `backend/src/db/repositories/editorial_session_repository.py`

API schemas and routing:
- `backend/src/schemas/workflow.py`
- `backend/src/api/v1/endpoints/workflows.py`
- `backend/src/api/v1/endpoints/versions.py` (keyword patch)

## Contract Rules (Do Not Break)

Keep these stable unless coordinated:
- `EditorialRequest`
- `EditorialResponse`
- version endpoint response shape (`ContentVersionEntity`)
- schema payloads in `workflow.py` used by UI and other team members

## Recommended Improvements

1. Stronger section-targeted editing in `editorial.py`.
2. Better diff-quality `change_log`.
3. Add guardrails for empty/degenerate edited content.
4. Improve outline-preserving rewrite behavior for regenerate-outline.
5. Add tests for:
   - finalize-selected pointer updates
   - variant-label carry-forward on editorial chain
   - feedback preview non-persistence

## Done Criteria

- Editorial endpoints preserve current contracts.
- Finalization reliably sets one final pointer/version.
- Downstream artifact + platform output generation still works after finalization.

---

## Backend Update Reference

Backend-side implemented changes (UI excluded) are tracked in [../../BACKEND_CHANGES.md](../../BACKEND_CHANGES.md).
