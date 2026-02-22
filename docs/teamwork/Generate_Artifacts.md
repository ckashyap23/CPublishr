# Artifacts Developer Guide

This guide explains how to add a new artifact format in the current architecture.

## Current model (important)

Each format is generated directly by a format builder module:
- input: context bundle + master content + seed keywords
- output: one `ArtifactDraft` in common schema

## Where to create a new file

Create a new file under:
- `backend/src/services/orchestration/artifacts/formats/`

Example:
- `backend/src/services/orchestration/artifacts/formats/short_reel.py`

----------------------------------------------------------------------
## What to implement in that file

Your file must expose a module-level `BUILDER`.

Mandatory requirements:
- You must define a builder class.
- Builder class must define `formats` and `kind` (or `format_kinds` for mixed kinds).
- Builder class must implement `build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft`. It consumes the input context and return a valid `ArtifactDraft`.
- Additional helper methods are allowed.
- You must export `BUILDER = <YourBuilderClass>()` at module level.
  `registry.py` (`discover_builders`) imports each file in `artifacts/formats` and checks for a module variable named exactly `BUILDER`; if it is missing, that file is ignored.

```python
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext
from src.services.orchestration.artifact_schema import default_payload_template

class ShortReelBuilder:
    kind = "video"  # or use format_kinds for mixed kinds
    formats = {"short_reel"}

    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        payload = default_payload_template()
        # build payload using ctx.context_bundle + ctx.master_body + ctx.seed_keywords
        return ArtifactDraft(
            format=fmt,
            title=f"{ctx.topic_title} - Short Reel",
            payload_json=payload,
            tags_json=list(ctx.seed_keywords),
        )

BUILDER = ShortReelBuilder()
```
------------------------------------------------------------------
## Where to register format + kind mapping

Registration is automatic through:
- `backend/src/services/orchestration/artifacts/formats/registry.py`

Rules:
- if your builder has one kind for all formats:
  - set `kind = "text|image|video|audio|gif|bundle"`
  - set `formats = {"your_format"}`
- if your builder handles multiple kinds:
  - set `format_kinds = {"fmt_a": "text", "fmt_b": "video"}`
  - set `formats = set(format_kinds.keys())`

`discover_builders` auto-discovers by importing each module and reading `module.BUILDER`.

-------------------------------------------------------------------

## Inputs available to your builder

Read from `PipelineContext` (`backend/src/services/orchestration/artifacts/contracts.py`):

- `ctx.context_bundle`: full Node 0 context bundle
- `ctx.master_body`: finalized editorial/master content
- `ctx.seed_keywords`: keywords from selected content version
- `ctx.topic_title`, `ctx.core_idea`
- `ctx.target_audience` (object with `primary_segment`, optional `notes`), `ctx.audience_familiarity`, `ctx.detail_level`, `ctx.tone_preference`
- `ctx.style_settings` (effective settings for the current format; may be shared request settings merged with per-format overrides)

----------------------------------------------------------------------

## Output schema you must follow

Return `ArtifactDraft`:
- `format: str`
- `title: str | None`
- `payload_json: dict`
- `tags_json: list[str]`
- optional: `status`, `revision`, `parent_artifact_id`

`payload_json` must follow common envelope (`default_payload_template()`):

```json
{
  "version": "1.0",
  "body": null,
  "items": [],
  "assets": [],
  "prompts": [],
  "settings": {},
  "notes": null
}
```

--------------------------------------------------------------------------
## Validation and persistence path

Generation flow:
1. API `POST /api/v1/artifacts/generate`
2. `ArtifactPipelineOrchestrator.generate(...)`
3. resolve builder by format (`registry.py`)
4. call `builder.build(fmt, ctx)`
5. normalize + validate (`artifact_schema.py`)
6. persist via `ArtifactRepository`

Note:
- Artifact generation is executed via `POST /api/v1/artifacts/generate` (on-demand).
- Current request contract supports:
  - `style_settings` (shared defaults across selected formats)
  - `style_settings_by_format` (per-format overrides, e.g. `image_generation`)
- Stage toggles (`stages.plan`, `stages.render_media`, etc.) are not part of the current request schema.
- Some builders may persist local outputs in `backend/src/services/orchestration/artifacts/formats/` (for example image files under `images/` and text exports under `text/`) and include those paths in artifact payloads.
- Some editorial finalize paths may run post-editorial pipeline, but `finalize-selected` itself only marks final version.

Example request (multi-format with image-specific settings):

```json
{
  "project_id": "proj_local_2",
  "requested_formats": ["caption", "x_post", "image_generation"],
  "revision_mode": "new_revision",
  "style_settings": {},
  "style_settings_by_format": {
    "image_generation": {
      "tool_name": "openai",
      "output_formats": ["png"],
      "size": "1024x1024",
      "quality": "standard",
      "style": "vivid"
    }
  }
}
```

-------------------------------------------------------------------------
## How UI gets new formats automatically

UI calls:
- `GET /api/v1/artifacts/catalog/formats`

This is populated from discovered builders, so your new format appears in UI automatically after backend restart.
--------------------------------------------------------------------------

## Quick checklist when adding a format

1. Create `backend/src/services/orchestration/artifacts/formats/<artifact_format_name>.py`
2. Add `BUILDER` with `formats` + `kind` (or `format_kinds`)
3. Implement `build(fmt, ctx) -> ArtifactDraft`
4. Use envelope schema for `payload_json`
5. Restart backend
6. Verify:
   - `GET /api/v1/artifacts/catalog/formats` includes your format
   - format appears in UI
   - `POST /api/v1/artifacts/generate` succeeds
   - format-specific settings only affect the intended builder (when using `style_settings_by_format`)
