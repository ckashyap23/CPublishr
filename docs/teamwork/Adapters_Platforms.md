# Adapters Platforms - Team Handoff Guide

This document clarifies where to change adapter behavior safely, and when additional files must be touched.

## Scope

There are now two platform-related areas:
- legacy editorial output adapters (older `services/platforms` flow)
- publish-stage adapters (current mapping + publish flow)

Current publish-stage adapters (active for Publish UI / `/api/v1/publishing/*`):
- `backend/src/platforms/adapters/linkedin.py`
- `backend/src/platforms/adapters/instagram.py`
- registry / discovery: `backend/src/platforms/adapters/registry.py`

## Publish Adapter Responsibilities (Current)

Adapters in `backend/src/platforms/adapters/*.py` are responsible for:
1. Declaring UI-facing platform fields (`get_field_schema`)
2. Combining mapped artifact sources into a platform payload (`build_platform_payload`)
3. Publishing to platform API (`publish`) - placeholder today, real integration later

## Input -> Processing -> Output (Publish Stage)

Current adapter input (from publish service):
- `field_mapping: dict[str, list[source]]`

Each `source` contains:
- `artifact_id`
- `part` (`title | body | tags_json | items | assets | ...`)
- `render_as` (optional adapter hint)
- `order`
- `artifact` (full artifact entity snapshot used for composition)

Current output:
- `build_platform_payload(...)` returns adapter-defined platform payload dict
- `publish(...)` returns normalized publish result dict (`status`, `external_id`, `external_url`, etc.)

## Logic-Only Changes (Safe, Preferred)

If you are only improving transformation logic, edit:
- `backend/src/platforms/adapters/*.py`

Examples:
- Better artifact-part composition (e.g., `post.body + tags_json`)
- Better hashtag rendering (`hashtags_line`, `hashtags_block`)
- Better CTA selection from `cta_variants.items`
- Better media asset extraction (`payload_json.assets`)
- Better platform-specific payload formatting before API call

### Constraints for logic-only changes

- Keep adapter API stable:
  - `get_field_schema() -> dict`
  - `build_platform_payload(field_mapping=...) -> dict`
  - `publish(payload=...) -> dict`
- If you change `get_field_schema()` field keys/types, coordinate UI mapping expectations.

## Wiring / Schema / Storage Changes (Cross-Team Impact)

If your change affects routing, contracts, or persistence, you must also modify related files.

### 1) Wiring changes

Edit:
- `backend/src/platforms/adapters/registry.py`
- `backend/src/api/v1/endpoints/publishing.py`
- `backend/src/services/publishing/service.py`

Examples:
- Add/remove platform adapter
- Change adapter discovery behavior
- Change mapping source payload passed to adapters

### 2) Schema changes

Edit:
- `backend/src/schemas/publishing_schemas.py`
- UI mapping payload builder in `ui/react/src/App.jsx`

Examples:
- `field_mappings` request shape change
- source-level mapping fields (`part`, `render_as`, `order`) changes
- publish job response payload shape changes

Rule:
- Treat schema changes as explicit API changes and coordinate UI + adapter owners.

### 3) Storage changes

Edit:
- `backend/src/db/models/publish_job.py`
- `backend/src/db/repositories/publish_repository.py`
- `backend/src/services/publishing/service.py`

Examples:
- Store richer publish payload snapshots
- Store adapter metadata, external IDs/URLs, error details
- Add scheduling/status tracking fields

## Suggested Improvements

Low-risk improvements:
1. Add stronger source validation in adapters (`part` + format compatibility).
2. Add per-platform helper utilities for body/tag/item composition.
3. Add deterministic source ordering and merge rules.
4. Add adapter-side payload validation before API call.

Medium-risk improvements:
1. Real LinkedIn/Instagram API integration (media upload + publish).
2. Async publish execution and retries.
3. Platform metrics fetch and job status monitoring.

## Test Guidance

Minimum:
- Adapter registry discovers the new adapter.
- `GET /api/v1/publishing/platforms` lists the adapter.
- `GET /api/v1/publishing/platforms/{platform}/fields` returns the expected field schema.
- `POST /api/v1/publishing/jobs/artifacts` accepts UI mappings and records a publish job (stub path).

Recommended:
- Unit tests for `build_platform_payload(...)` using source-part mappings.
- Regression tests for mixed mappings (body + tags + items).
- Validation tests for required/optional field behavior.

## Done Criteria

- Adapter behavior improved.
- No publish API contract break without coordinated UI update.
- `Publish` UI can load platform fields and map artifacts successfully.
- If wiring/schema/storage changed, all related files/docs updated in same PR.
