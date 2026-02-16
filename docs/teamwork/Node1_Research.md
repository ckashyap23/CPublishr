# Node1 Research - Team Handoff Guide

This document defines how to evolve Node 1 (Research) without breaking downstream nodes.

## Goal

Own research generation logic while keeping input/output contracts stable for parallel work.

## Endpoint Entry Points

- Preferred isolated testing endpoint: `POST /api/v1/workflows/nodes/research`
  - Body: `{ "topic": TopicInitializationRequest, "persist_context": bool }`
- Existing project-based endpoint: `GET /api/v1/workflows/nodes/research/{project_id}`

Important:
- `POST /api/v1/projects/` for an existing `project_id` resets prior project-scoped rows for that project before saving fresh Node 0 context.

## Contract Rules

Node 1 output must stay exactly:
- `research_summary: string`
- `emerging_tools: string[]`
- `recent_discussions: string[]`
- `key_insights: string[]`
- `contrarian_angles: string[]`

Do not change Node 1 contract fields in `backend/src/contracts/prd.py` unless coordinated.

## Files To Change

Primary:
- `backend/src/services/orchestration/nodes/research_trends.py`

Optional internal modules:
- `backend/src/services/research/serp_client.py`
- `backend/src/services/research/reranker.py`
- `backend/src/services/research/pipeline.py`

Avoid changing orchestration wiring unless required:
- `backend/src/services/orchestration/engine.py`

## Input Boundary

Node 1 reads from `context.state["context_bundle"]`.

Expected available fields:
- `topic_title`
- `normalized_topic`
- `core_idea`
- `user_content`
- `target_audience`
- `content_depth`
- `tone_preference`
- `distribution_targets`

Use defensive defaults for missing values.

### Sample Node 0 Output Fixture

```json
{
  "project_id": "proj_team_001",
  "normalized_topic": "multi-agent ai content orchestration",
  "context_bundle": {
    "topic_title": "Multi-Agent AI Content Orchestration",
    "normalized_topic": "multi-agent ai content orchestration",
    "core_idea": "Generate one canonical master document, then adapt packaging per platform.",
    "user_content": "Imagine your content as a movie script: you write one master doc, and a crew of AI \"agents\" turns it into trailers, posters, and behind-the-scenes clips automatically. One agent makes a punchy LinkedIn post, another crafts an Instagram carousel, a third writes a Twitter/X thread, and a fourth adapts it into a YouTube short script. Same core story, different costumes, different stage. The fun part? You stop rewriting from scratch and start directing the message while your agents handle the platform-specific polish.",
    "target_audience": "builders",
    "content_depth": "intermediate",
    "tone_preference": "professional",
    "distribution_targets": ["linkedin", "x", "medium", "github"]
  }
}
```

## Output Boundary

Node 1 must return:

```python
NodeExecutionResult(
    status="completed",
    output_payload={
        "research_summary": "...",
        "emerging_tools": ["..."],
        "recent_discussions": ["..."],
        "key_insights": ["..."],
        "contrarian_angles": ["..."],
    },
)
```

And keep:

```python
context.state["research"] = output
```

## Implementation Pattern

1. Gather candidates from 2-3 sources.
2. Normalize to one internal shape.
3. Filter and dedupe low-signal items.
4. Rank deterministically first; optional LLM rerank second.
5. Synthesize contract output and validate before return.

Recommended validation:
- `ResearchTrendResponse.model_validate(output)`

## Testing Checklist

Minimum:
- Valid output shape even if external APIs fail.
- Deterministic enough behavior for repeatable tests (or mocks).

Recommended:
- Unit tests for dedup/ranking.
- Unit tests for fallback behavior.
- Contract validation tests.

## Done Criteria

- Output contract unchanged and valid.
- Node 2 consumes `context.state["research"]` unchanged.
- External failures degrade gracefully with valid fallback output.
