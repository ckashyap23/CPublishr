# Node 1 Research

Node 1 enriches a project topic with structured research signals for Node 2.

## Runtime Surface

| Purpose | Endpoint |
|---------|----------|
| Run research for a saved project | `GET /api/v1/workflows/nodes/research/{project_id}` |
| Run research with an explicit topic payload | `POST /api/v1/workflows/nodes/research` |

Main implementation:

- `backend/src/services/orchestration/nodes/research_trends.py`
- `backend/src/schemas/workflow.py`
- `backend/src/contracts/prd.py`

## Input

Node 1 reads `context.state["context_bundle"]`, created by Node 0.

Required fields:

- `topic_title`
- `normalized_topic`
- `core_idea`
- `target_audience.primary_segment`
- `tone_preference`
- `voice_profile_id`

Optional fields:

- `user_content`
- `target_audience.notes`
- `audience_familiarity`
- `detail_level`
- `stance`
- `primary_goal`
- `desired_action`
- `constraints`
- `distribution_targets`

Use defensive defaults for optional or missing values.

## Output Contract

Node 1 must return `ResearchTrendResponse`:

```json
{
  "research_summary": "...",
  "emerging_tools": ["..."],
  "recent_discussions": ["..."],
  "key_insights": ["..."],
  "contrarian_angles": ["..."]
}
```

The node also sets:

```python
context.state["research"] = output
```

Do not rename or remove output fields without updating Node 2, API schemas, tests, and the UI.

## Implementation Rules

- Normalize source data into one internal shape before ranking.
- Deduplicate low-signal or repeated items.
- Prefer deterministic ranking before optional LLM reranking.
- External API failures must return a valid fallback response.
- Validate final output with `ResearchTrendResponse.model_validate(output)`.

## Test Checklist

- Valid output shape with normal input.
- Valid fallback output when external sources fail.
- Deterministic ranking/deduping behavior, or mocked non-determinism.
- Node 2 still consumes `context.state["research"]`.
