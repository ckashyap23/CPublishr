# Artifact Generation - Team Handoff Guide

This document defines how to split artifact generation work safely across team members.

## Goal

Generate artifacts from finalized editorial content using a staged pipeline:
- `plan` -> `prompt_pack` -> `render_media` -> `assemble` -> `package`

Maintain one stable artifact schema across all formats and kinds.

## Endpoints and Entry Points

Primary API:
- `POST /api/v1/artifacts/generate`
- `GET /api/v1/artifacts/{project_id}`
- `GET /api/v1/artifacts/{project_id}/{format}`
- `GET /api/v1/artifacts/{project_id}/kind/{kind}`

Workflow-triggered path (post-editorial finalize):
- `POST /api/v1/workflows/nodes/editorial/finalize-selected`
- engine post-finalization path writes artifacts and adapter outputs

## Single Source of Truth

Artifact format/kind mapping and envelope:
- `backend/src/services/orchestration/artifact_schema.py`

Core rules:
- `kind` is server-derived from `format`
- `payload_json` uses universal envelope keys only:
  - `version`, `body`, `items`, `assets`, `prompts`, `settings`, `notes`
- `tags_json` is artifact-level metadata (not inside payload)

## Current Pipeline Wiring

Orchestrator:
- `backend/src/services/orchestration/artifacts/orchestrator.py`

Stages:
- `backend/src/services/orchestration/artifacts/stages/plan_text.py`
- `backend/src/services/orchestration/artifacts/stages/prompt_pack.py`
- `backend/src/services/orchestration/artifacts/stages/render_media.py`
- `backend/src/services/orchestration/artifacts/stages/assemble_media.py`
- `backend/src/services/orchestration/artifacts/stages/package_bundle.py`

Persistence:
- model: `backend/src/db/models/artifact.py`
- repo: `backend/src/db/repositories/artifact_repository.py`

-----------------------------------------------------------------------
## Example Implementation Flows

### Flow A: Build a GIF (`gif_storyboard` -> `gif_loop`)

Goal:
- Generate frame-level storyboard, then assemble a looping GIF.

Request:
- include `gif_storyboard` and/or `gif_loop` in `requested_formats`.

Step-by-step:
1. Prompt planning
- file: `backend/src/services/orchestration/artifacts/stages/prompt_pack.py`
- generate `gif_storyboard` payload:
  - `items[]` with `item_type="frame"`, `sequence`, `prompt`, optional `timing_sec`
  - `settings` with loop/fps defaults

2. (Optional) frame rendering
- file: `backend/src/services/orchestration/artifacts/stages/render_media.py`
- if you introduce image-frame rendering for GIF, attach frame URIs into assets/meta.

3. Assembly
- file: `backend/src/services/orchestration/artifacts/stages/assemble_media.py`
- map storyboard frames -> frame asset list
- call ffmpeg assembler for GIF output

4. Media backend
- file: `backend/src/services/media/ffmpeg_service.py`
- implement/tune actual GIF assembly command and settings

5. Schema mapping (only if new format needed)
- file: `backend/src/services/orchestration/artifact_schema.py`
- ensure format is present in `KIND_BY_FORMAT` and maps to `gif`.

Expected artifact outputs:
- `gif_storyboard` (kind `gif`)
- `gif_loop` (kind `gif`, primary GIF asset URI)

### Flow B: Build a Short Reel (`storyboard` -> `video`)

Goal:
- Generate scene storyboard, render media clips/assets, then assemble final MP4 reel.

Request:
- include `storyboard`, `video`, optionally `voiceover_audio`.

Step-by-step:
1. Storyboard planning
- file: `backend/src/services/orchestration/artifacts/stages/prompt_pack.py`
- generate `storyboard` payload:
  - `items[]` with `item_type="scene"`, `sequence`, `prompt`, `text`, `timing_sec`
  - `settings` with aspect ratio and target duration

2. Clip/audio rendering
- file: `backend/src/services/orchestration/artifacts/stages/render_media.py`
- generate scene clips via video provider
- generate optional voiceover via TTS provider
- persist intermediate assets in stage draft payloads

3. Provider integrations
- file: `backend/src/services/media/video_provider.py`
- file: `backend/src/services/media/tts_provider.py`
- implement provider-specific API calls, retries, and URI returns

4. Final assembly
- file: `backend/src/services/orchestration/artifacts/stages/assemble_media.py`
- build timeline from rendered assets and storyboard order
- attach voiceover/subtitles if available
- emit final `video` artifact payload asset

5. FFMPEG details
- file: `backend/src/services/media/ffmpeg_service.py`
- encode settings, concat behavior, audio mix/subtitle overlay

6. Schema mapping (only if new format needed)
- file: `backend/src/services/orchestration/artifact_schema.py`
- ensure new/changed reel formats map to kind `video`.

Expected artifact outputs:
- `storyboard` (kind `video`)
- `video` (kind `video`, primary MP4 asset URI)
- optional `voiceover_audio` (kind `audio`)


----------------------------------------------------------------
## Suggested Team Split

### Track A - Text Artifacts
Owner scope:
- formats: `caption`, `x_post`, `x_thread`, `blog_*`, `newsletter`, `script_*`, `hook_bank`, `headline_variants`, `cta_variants`, `faq`, `playbook`
- stage: `plan`

Files:
- `backend/src/services/orchestration/artifacts/stages/plan_text.py`
- `backend/src/services/orchestration/artifact_schema.py` (only when adding/removing formats)

Responsibilities:
- prompt quality
- shape-normalization per format
- LLM fallback behavior
- tag generation quality

### Track B - Prompt Packs (Image/Video/GIF Planning)
Owner scope:
- formats: `image_prompt_pack`, `storyboard`, `gif_storyboard`
- stage: `prompt_pack`

Files:
- `backend/src/services/orchestration/artifacts/stages/prompt_pack.py`

Responsibilities:
- prompt structure
- timing/scene/frame schemas
- style settings propagation

### Track C - Media Rendering
Owner scope:
- formats: `image`, `voiceover_audio`, preview `video` clips
- stage: `render_media`

Files:
- `backend/src/services/orchestration/artifacts/stages/render_media.py`
- `backend/src/services/media/image_provider.py`
- `backend/src/services/media/video_provider.py`
- `backend/src/services/media/tts_provider.py`

Responsibilities:
- provider abstraction
- URI/asset metadata shape
- timeout/retry strategy

### Track D - Assembly (Video/GIF)
Owner scope:
- formats: assembled `video`, `gif_loop`
- stage: `assemble`

Files:
- `backend/src/services/orchestration/artifacts/stages/assemble_media.py`
- `backend/src/services/media/ffmpeg_service.py`

Responsibilities:
- timeline build logic
- ffmpeg assembly options
- output asset consistency

### Track E - Bundling and Cross-Stage Packaging
Owner scope:
- format: `bundle`
- stage: `package`

Files:
- `backend/src/services/orchestration/artifacts/stages/package_bundle.py`

Responsibilities:
- artifact reference payload structure
- role mapping and sequence stability

### Track F - API, Persistence, DB
Owner scope:
- endpoint contracts
- DB model/repository compatibility
- migration/init compatibility scripts

Files:
- `backend/src/api/v1/endpoints/artifacts.py`
- `backend/src/schemas/artifacts.py`
- `backend/src/db/models/artifact.py`
- `backend/src/db/repositories/artifact_repository.py`
- `backend/src/db/init_db.py`

Responsibilities:
- response consistency
- backward compatibility guards
- schema cleanup and bootstrap safety

## Coordination Rules

1. If adding a format:
- update `KIND_BY_FORMAT` in `artifact_schema.py`
- ensure stage ownership is explicit
- add tests for shape and persistence

2. Do not add new ad-hoc keys inside `payload_json` unless coordinated.

3. Keep API request/response contracts stable unless all owners align.

4. If DB schema changes:
- update `artifact.py`
- update `init_db.py` compatibility logic
- validate against existing Postgres instances

## Testing Checklist

Minimum:
- `POST /api/v1/artifacts/generate` works for one text format and one media-related format.
- artifacts persist with:
  - non-null `format`, `kind`, `payload_json`, `tags_json`
  - valid revision semantics

Recommended:
- per-stage unit tests for shape normalization
- integration test with multi-format request
- regression tests for legacy DB columns

## Done Criteria

- each owned stage works independently and with adjacent stages
- generated artifacts are contract-valid and queryable by project/format/kind
- UI can generate and inspect artifacts without backend 500s
