# Node3 Editorial - Team Handoff Guide

This document defines how to improve Node 3 (`editorial.py`) without breaking API and workflow compatibility.

## Goal

Own the editorial logic for:
- single-pass edits
- iterative draft refinement
- finalizing accepted content into versioned master content

while preserving all existing contracts.

## Current Files and Responsibilities

Primary node file:
- `backend/src/services/orchestration/nodes/editorial.py`

Orchestration and session lifecycle:
- `backend/src/services/orchestration/engine.py`

Editorial session persistence:
- `backend/src/db/models/editorial_session.py`
- `backend/src/db/repositories/editorial_session_repository.py`

Endpoints:
- `backend/src/api/v1/endpoints/workflows.py`

Schemas (API/session payloads):
- `backend/src/schemas/workflow.py`
- `backend/src/contracts/prd.py` (`EditorialRequest`, `EditorialResponse`)

## How Node 3 Works Today

### Input to Node 3

Node receives:
- `context.input_payload`
  - `project_id`
  - `current_version`
  - `editor_actions[]`
  - `user_feedback`
- `context.state["current_master_document"]`
  - current content to edit

### Processing

1. Build action log from `editor_actions`.
2. Apply editorial update with deterministic fallback formatting.
3. If Azure OpenAI is configured, ask the LLM to return strict JSON with:
   - `updated_master_document`
   - `change_log`
4. Fallback remains active if LLM call fails.

### Output from Node 3

Must return exactly:

```json
{
  "draft_version": 2,
  "updated_master_document": "markdown...",
  "change_log": ["..."]
}
```

## Two Operational Modes

### Mode A: Single-Pass Editorial

Endpoint:
- `POST /api/v1/workflows/nodes/editorial`

Flow:
1. Load requested version from `content_versions`.
2. Run Node 3 once.
3. Persist new `ContentVersion` immediately with `version_kind="editorial"`.

### Mode B: Iterative Session Editorial

Endpoints:
1. `POST /api/v1/workflows/nodes/editorial/session/start`
2. `POST /api/v1/workflows/nodes/editorial/session/{session_id}/iterate`
3. `POST /api/v1/workflows/nodes/editorial/session/{session_id}/finalize`

Flow:
1. Start session from base version and first comment.
2. Iterate with additional comments while storing temporary `working_content`.
3. Finalize writes accepted content as a new `ContentVersion`.

## Non-Negotiable Contract Rules

Do not change these shapes without cross-team approval:

### PRD Editorial Contract
- `EditorialRequest`
- `EditorialResponse`

Required output keys:
- `draft_version: int`
- `updated_master_document: str`
- `change_log: list[str]`

Note:
- persisted editorial version number is assigned by repository next-version logic (global project sequence).

### Session API Schemas (workflow.py)
Keep fields stable for:
- `EditorialSessionStartRequest/Response`
- `EditorialSessionIterateRequest/Response`
- `EditorialSessionFinalizeResponse`

## Recommended Improvement Areas

1. Better edit targeting
- Section-aware editing instead of full-document rewrite.
- Respect `target_section` strongly.

2. Better iteration memory
- Track what changed each iteration.
- Avoid reintroducing previous issues.

3. Quality gates
- Validate markdown structure before persisting.
- Ensure no empty/degenerate output.

4. Diff and audit quality
- Improve `change_log` with meaningful, user-readable updates.

5. LLM robustness
- Stronger prompt format.
- Structured JSON parsing guards.
- Reliable fallback behavior on API failures/timeouts.

## Suggested Internal Architecture

Keep `editorial.py` as orchestration logic and move heavy internals to:
- `backend/src/services/editorial/formatter.py`
- `backend/src/services/editorial/diff.py`
- `backend/src/services/editorial/quality.py`
- `backend/src/services/editorial/prompting.py`

This keeps Node 3 readable and testable.

## Test Checklist

Minimum:
- Single-pass endpoint creates new version.
- Session start creates temporary draft.
- Session iterate updates draft and increments iteration.
- Session finalize persists final version.
- Output always validates as `EditorialResponse`.

Recommended tests:
- Empty/invalid feedback handling.
- LLM failure fallback path.
- Repeated finalize/iterate invalid state handling.

## Coordination Rules (So Others Are Not Blocked)

- Do not change Node 3 output keys/types.
- Do not change how final version is persisted on finalize.
- Keep Node 3 compatible with Node 2 output markdown.
- Avoid introducing dependencies that require Node 1/2 schema changes.

## Done Criteria for Node 3 Owner

- Editorial quality improved (single-pass + iterative).
- Contracts unchanged and valid.
- Session lifecycle stable under repeated use.
- Finalized content is reliably persisted as new master version.
