# Adapters Platforms - Team Handoff Guide

This document clarifies where to change adapter behavior safely, and when additional files must be touched.

## Scope

Adapters convert finalized editorial content into platform-specific outputs.

Current files:
- `backend/src/services/platforms/adapters/linkedin.py`
- `backend/src/services/platforms/adapters/x.py`
- `backend/src/services/platforms/adapters/youtube.py`
- `backend/src/services/platforms/adapters/instagram.py`
- `backend/src/services/platforms/adapters/substack.py`
- `backend/src/services/platforms/adapters/medium.py`
- `backend/src/services/platforms/adapters/github.py`

## Input -> Processing -> Output

Common input to each adapter:
- `master_document: str` (finalized editorial markdown)
- `context: dict` (Node 0 + Node 2 metadata)

Common processing pattern:
1. Read relevant fields from `context` (`topic_title`, `normalized_topic`, `core_idea`, `user_content`, etc.)
2. Apply platform-specific formatting rules
3. Return a contract-compliant structured dict

Output contracts (must match `backend/src/contracts/prd.py`):
- LinkedIn: `LinkedInOutput`
- X: `XOutput`
- YouTube: `YouTubeOutput`
- Instagram: `InstagramOutput`
- Substack: `SubstackOutput`
- Medium: `MediumOutput`
- GitHub: `GitHubOutput`

## Logic-Only Changes (Safe, Preferred)

If you are only improving transformation logic, edit:
- `backend/src/services/platforms/adapters/*.py`

Examples:
- Better summarization/chunking
- Better hashtag/tag selection
- Better chapter/outline extraction
- Better CTA formatting
- Better markdown cleanup

### Constraints for logic-only changes

- Do not change output keys.
- Do not change output value types.
- Keep return shape contract-valid for the platform.
- Do not change adapter method signature: `transform(master_document, context) -> dict`.

## Wiring / Schema / Storage Changes (Cross-Team Impact)

If your change affects routing, contracts, or persistence, you must also modify related files.

### 1) Wiring changes

Edit:
- `backend/src/services/platforms/registry.py`
- `backend/src/services/orchestration/engine.py`

Examples:
- Add/remove platform adapter
- Change how context is passed to adapters
- Change which targets are executed in run flow

### 2) Schema changes

Edit:
- `backend/src/contracts/prd.py`
- `backend/contracts/examples/adapter_*.response.json`
- `backend/tests/unit/test_prd_contract_examples.py`

Examples:
- New output fields
- Field rename/type change

Rule:
- Treat schema changes as explicit API/contract changes and coordinate with all node owners.

### 3) Storage changes

Edit:
- `backend/src/db/models/platform_output.py`
- `backend/src/db/repositories/content_repository.py`
- `backend/src/api/v1/endpoints/platform_outputs.py`

Examples:
- Store richer metadata per output
- Store parsed JSON vs stringified JSON
- Add output versioning/indexing

## Suggested Improvements

Low-risk improvements:
1. Add stronger fallback behavior when input content is sparse.
2. Add per-platform helper utilities for text normalization.
3. Add deterministic output ordering for test stability.
4. Add lightweight in-adapter validation against PRD models.

Medium-risk improvements:
1. Add LLM-assisted refinement per adapter with strict fallback.
2. Add platform-specific scoring (clarity/length/format compliance).
3. Add configurable adapter profiles by audience/tone.

## Test Guidance

Minimum:
- Each adapter output validates against corresponding PRD contract model.
- Existing API endpoint `/api/v1/platform-outputs/{project_id}` remains unchanged.

Recommended:
- Unit tests per adapter with fixed input snapshot.
- Regression tests for edge cases (empty master doc, long master doc, missing context).

## Done Criteria

- Adapter behavior improved.
- No contract break.
- No regressions in workflow run or platform output retrieval.
- If wiring/schema/storage changed, all related files/tests updated in same PR.
