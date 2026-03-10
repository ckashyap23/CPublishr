# Backend Changes (UI Excluded)

This document summarizes backend-side changes currently implemented in the codebase.

## 1. Prompt Logging to Azure Blob (`qc-prompts`)

- Added prompt blob storage service at `backend/src/services/storage/prompt_blob_storage.py`.
- Prompt logs are saved to Azure prompts container (default: `qc-prompts`) with configurable prefix.
- Prompt logging is now used by orchestration paths (research/editorial/master-content/artifact orchestration integration points).

## 2. Artifact Storage and Blob Path Handling

- Added artifact persistence helper module at `backend/src/services/orchestration/artifacts/persistence.py`.
- Artifact payloads now carry blob path metadata more consistently (`asset.blob_path`) for downstream refresh/reuse.
- Added/expanded blob URL refresh and blob-path extraction logic in artifact/publishing flows.

## 3. Artifact Orchestration + Builder Contract Evolution

- Artifact orchestrator and builders were updated to support iterative generation with richer source context:
  - `source_blob_paths`
  - source artifact resolution by blob path
  - target artifact overwrite/versioning hooks
- Format builders (`text`, `image`, `video`) were updated to align with the expanded edit/build contract and payload shape.

## 4. Video Artifact Backend Enhancements

- Video generation flow includes clip-level asset tracking with provider/job metadata.
- Export steps (reel/short video/gif) persist final outputs with blob metadata when available.
- Stitch/convert paths are handled with ffmpeg best-effort strategy and error propagation into payload settings.

## 5. Publishing Backend Hardening

- Publishing services and endpoints were updated to improve output-path handling and safer URL regeneration.
- Output destination validation now explicitly rejects unsupported HTTP(S)-style output roots where not allowed.
- Platform/payload normalization and artifact mapping behavior were tightened in service/repository layers.

## 6. API/Repository/Schema Alignment

- Endpoint updates across:
  - `artifacts`
  - `publishing`
  - `platform_outputs`
  - `projects`
  - `versions`
  - `workflows`
- Repository updates across artifact/content/project/publish stores for new metadata + lookup behavior.
- Schema/config updates to support new backend options and payload fields.

## 7. Test Coverage Updates

- Backend tests were updated to reflect new context/payload and workflow behavior:
  - `backend/tests/integration/test_workflow_happy_path.py`
  - `backend/tests/unit/test_context_bundle_schema.py`

## 8. Artifact Prompt Quality Improvements

### Image builder (`image_generation.py`)

- Added `_IMAGE_ENUM_EXPANSIONS` dict: raw dropdown values (e.g. `"muted"`, `"3d_render"`) are now expanded to descriptive phrases before prompt injection (e.g. `"muted desaturated tones, soft contrast"`, `"3D CGI render"`). Unknown values pass through unchanged.
- Added `_expand_image_enum()` helper function used by `_build_prompt()`.
- Added `lighting` as a new user-supplied style field (12 options, same set as video). Injected as `"Lighting: ..."` in the visual style section of the prompt.
- Updated all 4 format `prompt_hint` values with precise per-format compositional rules:
  - `post_image`: visual anchor requirement, bottom ~15% caption safe zone, no flat symmetrical layouts.
  - `thumbnail`: 60–70% frame height for subject, eyes-in-upper-third rule, warm-cool foreground/background contrast.
  - `cover`: explicit 80% safe zone (10% margin all edges), lower-20% tonal gradient for title overlay.
  - `banner`: subject anchored left third with shallow DoF, right two-thirds kept plain, panoramic feel.

### Video builder (`video_artifacts.py`)

- Added `_VIDEO_ENUM_EXPANSIONS` dict and `_expand_video_enum()` helper: same pattern as image — all dropdown values expanded to descriptive phrases before injection.
- Added `_VIDEO_ENERGY_LEVEL_MAP`: maps `low/medium/high` → `(pacing, motion_intensity)` tuple used to override recipe composition defaults.
- Added `_SHORT_VIDEO_SEGMENT_ROLES`: per-segment narrative arc (establishing → development × 3 → resolution) injected by `_build_segments()` when clip count is 5.
- Fixed GIF recipe `camera_motion`: was `"static_tripod"` (contradicted the cyclical-motion requirement); changed to `"subtle_oscillating_loop"`.
- Added `reel` in-prompt rule: 9:16 full bleed, upper-65% framing, explicit first-2-second hook definition.
- Updated `short_video` in-prompt rule: full narrative arc with per-segment role descriptions.
- Added `camera_motion` as a new user-supplied style field: overrides the recipe's hardcoded `composition_defaults["camera_motion"]` when provided.
- Added `energy_level` as a new user-supplied style field (`low/medium/high`): expands to `(pacing, motion_intensity)` overrides on top of recipe defaults and appended as "Overall energy: ..." in the prompt.
- `_normalized_video_style_snapshot()` now includes `camera_motion` and `energy_level`.

## Notes

- This changelog intentionally excludes frontend/UI work.
- If you want, this can be split into per-module changelogs under `docs/teamwork/` next.
