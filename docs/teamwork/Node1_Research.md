# Node1 Research - Team Handoff Guide

This document defines how to implement and evolve Node 1 (Research) without breaking downstream nodes (especially Node 2).

## Goal

Own the full logic for research generation while keeping input/output contracts stable so parallel backend work can continue safely.

Node 1 can include:
- Multiple SERP/API calls
- Source filtering
- Deduplication
- Re-ranking
- Heuristic or LLM-assisted summarization
- Contrarian angle generation

## Node 0 Input Schema (Latest)

Required:
- `topic_title`
- `core_idea`
- `tone_preference`
- `distribution_targets`

Optional:
- `user_content`
- `target_audience`
- `content_depth`

## Non-Negotiable Contract Rule

Node 1 output schema must remain exactly:

- `research_summary: string`
- `emerging_tools: string[]`
- `recent_discussions: string[]`
- `key_insights: string[]`
- `contrarian_angles: string[]`

Do not change `backend/src/contracts/prd.py` for Node 1 work unless there is an explicit cross-team schema change decision.

## Files You Should Change

Primary:
- `backend/src/services/orchestration/nodes/research_trends.py`

Optional shared helper changes:
- `backend/src/services/llm/azure_openai.py` (if common request/parsing helpers are needed)

Recommended new internal modules (safe to add):
- `backend/src/services/research/serp_client.py`
- `backend/src/services/research/reranker.py`
- `backend/src/services/research/pipeline.py`
- `backend/src/services/research/models.py` (internal-only typed structures)

Usually avoid changing:
- `backend/src/services/orchestration/engine.py`

Only touch engine if absolutely needed for dependency wiring, and keep execution order unchanged.

## Input Boundary (What Node 1 Receives)

Node 1 reads from:
- `context.state["context_bundle"]`

Useful fields available:
- `topic_title`
- `normalized_topic`
- `core_idea`
- `user_content`
- `target_audience`
- `content_depth`
- `tone_preference`
- `distribution_targets`

Treat missing fields defensively with defaults.

### Sample Node 0 Output (Use This As Input Fixture)

Node 1 typically receives this through `context.state["context_bundle"]`:

```json
{
  "project_id": "proj_team_001",
  "normalized_topic": "multi-agent ai content orchestration",
  "context_bundle": {
    "topic_title": "Multi-Agent AI Content Orchestration",
    "normalized_topic": "multi-agent ai content orchestration",
    "core_idea": "Generate one canonical master document, then adapt packaging per platform.",
    "user_content": "Imagine your content as a movie script: you write one master doc, and a crew of AI “agents” turns it into trailers, posters, and behind-the-scenes clips—automatically. One agent makes a punchy LinkedIn post, another crafts an Instagram carousel, a third writes a Twitter/X thread, and a fourth adapts it into a YouTube short script. Same core story, different costumes, different stage. The fun part? You stop rewriting from scratch and start “directing” the message—while your agents handle the platform-specific polish.",
    "target_audience": "builders",
    "content_depth": "intermediate",
    "tone_preference": "professional",
    "distribution_targets": ["linkedin", "x", "medium", "github"]
  }
}
```

When testing Node 1 in isolation, you can set:

```python
context.state["context_bundle"] = SAMPLE["context_bundle"]
```

## Output Boundary (What Node 1 Must Return)

Inside `ResearchTrendsNode.run(...)`, always return:

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

This is required for Node 2 compatibility.

## Recommended Implementation Pattern

1. Gather candidates
- Query 2-3 sources (SERP/news/docs/community APIs).
- Normalize into a common internal record format.

2. Filter and dedupe
- Drop low-signal or duplicate entries.
- Keep only recent/relevant records.

3. Rank
- Rank with deterministic heuristics first (recency, source quality, topic match).
- Optionally add LLM reranking after deterministic shortlist.

4. Synthesize contract output
- Build concise summary + structured lists.
- Keep list sizes bounded and stable (example: 3-7 items each).

5. Validate before returning
- Call `ResearchTrendResponse.model_validate(output)` in-node before return (recommended guard).

## Coding Guidelines

- Keep external API logic isolated under `services/research/*`.
- Keep `research_trends.py` as orchestrator/composer only.
- Handle API failures gracefully with fallback output.
- Avoid leaking provider-specific response shapes outside `services/research/*`.
- Log useful diagnostics, but do not log secrets.

## Testing Checklist

Minimum:
- Node returns valid contract shape even on upstream API failures.
- Output is deterministic enough for repeatable tests (or mock external calls).

Recommended tests to add:
- Unit test for ranking/dedup logic.
- Unit test for fallback behavior when external APIs fail.
- Unit test that validates final output against `ResearchTrendResponse`.

Existing contract guard:
- `backend/tests/unit/test_prd_contract_examples.py`

## Coordination Rules (So Node 2 work is not blocked)

- Do not rename/remove required output keys.
- Do not change data types for output keys.
- Do not change how Node 1 writes to `context.state["research"]`.
- If you believe schema must change, raise a cross-team change request first.

## Done Criteria for Node 1 Owner

- Research logic is modularized and isolated from Node 2.
- Node 1 output passes `ResearchTrendResponse` validation.
- Node 2 runs unchanged and consumes `context.state["research"]` successfully.
- External failures degrade gracefully (fallback output still valid).
