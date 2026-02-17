# Node2 Master Content - Team Handoff Guide

This document defines how to improve Node 2 (`master_content.py`) without breaking downstream compatibility.

## Goal

Convert Node 0 + Node 1 context into a canonical base master document and optional variant master documents.

## Endpoint Entry Points

- Preferred isolated testing endpoint: `POST /api/v1/workflows/nodes/master`
  - Body:
    - `topic: TopicInitializationRequest` (required)
    - `research: ResearchTrendResponse` (optional override)
    - `persist_context: bool` (optional)
    - `persist_versions: bool` (optional)
- Existing project-based endpoint: `GET /api/v1/workflows/nodes/master/{project_id}`

Important:
- `POST /api/v1/projects/` for an existing `project_id` resets prior project-scoped rows for that project before saving fresh Node 0 context.

## Current Behavior

1. Reads `context.state["context_bundle"]` from Node 0.
2. Reads `context.state["research"]` from Node 1.
3. Produces base `master_document`.
4. Produces base `structure_outline` as a section map (H2 headings in order).
5. Produces base `core_arguments`.
6. Optionally produces `master_variants` with variant label + content + section map.
7. Stores output in `context.state["master"]`.

## Contract (Must Stay Stable)

Node 2 output (`MasterContentResponse`) fields:
- `master_document: string`
- `structure_outline: string[]`
- `core_arguments: string[]`
- `master_variants?: { label: string, master_document: string, structure_outline: string[], core_arguments: string[] }[]`

## Upstream Inputs

### Node 0 context bundle

Required Node 0 inputs (reference):
- `topic_title`, `core_idea`, `tone_preference`, `distribution_targets`

Optional Node 0 inputs:
- `user_content`, `target_audience`, `content_depth`

### Node 1 research payload

- `research_summary`
- `emerging_tools`
- `recent_discussions`
- `key_insights`
- `contrarian_angles`

## Downstream Usage

Node 2 output is used by:
- Editorial flow as source content.
- Adapter generation indirectly, after editorial finalization (finalized editorial content is the adapter input).
- Content version persistence.

Persistence behavior:
- Base document saved as `content_versions` row with:
  - `version_kind="base"`
  - `version_stage="draft"`
  - `keywords_json` from `core_arguments`
  - `structure_outline_json` from `structure_outline`
- Each variant saved as separate `content_versions` row with:
  - `version_kind="variant"`
  - `variant_label`
  - `version_stage="draft"`
  - `source_version_number=<base version number>`
  - its own `keywords_json` + `structure_outline_json`

## Required Output Example

```json
{
  "master_document": "# ...markdown...",
  "structure_outline": ["Hook", "Core Idea", "Section 1", "Section 2", "Section 3", "Key Takeaways", "Close"],
  "core_arguments": ["..."],
  "master_variants": [
    {
      "label": "Balanced (50/50) - Problem/Solution",
      "master_document": "# ...variant markdown...",
      "structure_outline": ["Hook", "Core Idea", "Section 1", "Section 2", "Section 3", "Key Takeaways", "Close"],
      "core_arguments": ["..."]
    }
  ]
}
```

## Implementation Guidance

1. Normalize and validate Node 0/Node 1 inputs.
2. Generate base document first.
3. Ensure base `structure_outline` is section-map semantics (not variant labels).
4. Generate variants; keep labels in `master_variants[*].label`.
5. Ensure each variant also has section-map `structure_outline`.
6. Validate output with `MasterContentResponse` before return.

## Avoid Breaking Changes

- Do not rename/remove Node 2 output keys.
- Do not change field types.
- Do not repurpose `structure_outline` back to variant labels.
- Do not bypass `context.state["master"]` output handoff.
- Keep `core_arguments` populated, since this now maps to persisted version keywords.

## Testing Checklist

Minimum:
- Contract-valid output for base + optional variants.
- Valid fallback behavior when LLM output is missing/bad.
- Node 3/editorial endpoints continue to work unchanged.

Recommended:
- Unit test that base `structure_outline` equals heading map.
- Unit test that variant outlines are heading maps.
- Integration test confirming base/variant versions persist with metadata.

## Done Criteria

- Output contract stable and valid.
- Base and variants are both usable in editorial flows via version numbers.
- Section outline semantics are consistent for base and variants.
