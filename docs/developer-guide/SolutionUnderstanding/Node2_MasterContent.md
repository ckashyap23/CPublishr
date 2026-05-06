# Node 2 Master Content

Node 2 turns project context and research into a canonical master document plus optional variants.

## Runtime Surface

| Purpose | Endpoint |
|---------|----------|
| Run master generation for a saved project | `GET /api/v1/workflows/nodes/master/{project_id}` |
| Run master generation with explicit topic/research payloads | `POST /api/v1/workflows/nodes/master` |

Main implementation:

- `backend/src/services/orchestration/nodes/master_content.py`
- `backend/src/services/orchestration/engine.py`
- `backend/src/schemas/workflow.py`
- `backend/src/contracts/prd.py`

## Inputs

Node 2 reads:

- `context.state["context_bundle"]` from Node 0
- `context.state["research"]` from Node 1

Required context fields:

- `topic_title`
- `normalized_topic`
- `core_idea`
- `target_audience.primary_segment`
- `tone_preference`
- `voice_profile_id`

Research fields:

- `research_summary`
- `emerging_tools`
- `recent_discussions`
- `key_insights`
- `contrarian_angles`

## Output Contract

Node 2 must return `MasterContentResponse`:

```json
{
  "master_document": "# ...markdown...",
  "structure_outline": ["Hook", "Core Idea", "Section", "Close"],
  "core_arguments": ["..."],
  "master_variants": [
    {
      "label": "Variant label",
      "master_document": "# ...markdown...",
      "structure_outline": ["Hook", "Core Idea", "Section", "Close"],
      "core_arguments": ["..."]
    }
  ]
}
```

The node also sets:

```python
context.state["master"] = output
```

## Persistence Semantics

The orchestration engine persists Node 2 output into `content_versions`.

| Output | Persisted as |
|--------|--------------|
| Base master document | `version_kind="base"`, `version_stage="draft"` |
| Each variant | `version_kind="variant"`, `version_stage="draft"`, `variant_label=<label>` |
| `core_arguments` | `keywords_json` |
| `structure_outline` | `structure_outline_json` |

Variant `source_version_number` points to the base version.

## Implementation Rules

- Generate and validate the base document first.
- Keep `structure_outline` as a section outline, not a list of variant labels.
- Keep variant labels only in `master_variants[*].label`.
- Populate `core_arguments`; downstream version keywords depend on it.
- Validate final output with `MasterContentResponse`.

## Test Checklist

- Contract-valid base output.
- Contract-valid variants when variants are requested.
- Fallback behavior when the LLM returns invalid or empty content.
- Persisted base/variant rows include correct metadata.
- Editorial endpoints can load generated versions by version number.
