# Node2 Master Content - Team Handoff Guide

This document defines how to improve Node 2 (`master_content.py`) without breaking downstream compatibility.

## Goal

Own the logic that converts Node 0 + Node 1 context into a high-quality canonical master document.

Node 2 should:
- Build a strong platform-neutral source document
- Preserve stable contracts for adapters and editorial flows
- Be independently improvable without schema drift

## Current File and Responsibility

Primary file:
- `backend/src/services/orchestration/nodes/master_content.py`

Current behavior:
1. Reads `context.state["context_bundle"]` from Node 0.
2. Reads `context.state["research"]` from Node 1.
3. Builds `master_document` markdown using title/core idea/research summary.
4. Returns `structure_outline` and `core_arguments` arrays.
5. Stores result in `context.state["master"]`.

## Non-Negotiable Contract Rule

Node 2 output schema must remain exactly:

- `master_document: string` (markdown)
- `structure_outline: string[]`
- `core_arguments: string[]`

Do not change key names or data types.

## Upstream Input Contracts (Must Be Supported)

### Node 0 Output (used via `context_bundle`)

```json
{
  "project_id": "proj_team_001",
  "normalized_topic": "multi-agent ai content orchestration",
  "context_bundle": {
    "topic_title": "Multi-Agent AI Content Orchestration",
    "normalized_topic": "multi-agent ai content orchestration",
    "core_idea": "Generate one canonical master document, then adapt packaging per platform.",
    "target_audience": "builders",
    "content_depth": "intermediate",
    "tone_preference": "professional",
    "distribution_targets": ["linkedin", "x", "medium", "github"]
  }
}
```

### Node 1 Output (used via `context.state["research"]`)

```json
{
  "research_summary": "Recent adoption shows teams prefer structured AI workflows over one-shot prompting.",
  "emerging_tools": ["LangGraph", "Temporal", "OpenTelemetry"],
  "recent_discussions": ["Reliability vs velocity", "Human-in-loop checkpoints"],
  "key_insights": ["Canonical source reduces drift", "Contracts improve team velocity"],
  "contrarian_angles": ["More agents is not always better"]
}
```

## Downstream Output Contract (Consumed by Node 3 / adapters)

Node 2 output is used by:
- Node 3 editorial flow (as current master content source)
- Platform adapters (transformations)
- Content version persistence

Required output shape:

```json
{
  "master_document": "# ...markdown...",
  "structure_outline": ["..."],
  "core_arguments": ["..."]
}
```

Any schema change here can break:
- editorial session workflows
- adapter generation
- API contract expectations

## Recommended Implementation Pattern

1. Input normalization
- Read Node 0 and Node 1 state safely with defaults.
- Validate minimum required signals (title/core idea/research summary).

2. Structured composition
- Build a stable section template, for example:
  - Hook
  - Core Idea
  - Why it matters now
  - Framework
  - Examples / tradeoffs
  - Conclusion

3. Research grounding
- Map Node 1 `key_insights` into argument sections.
- Map `contrarian_angles` into balanced/counterpoint sections.
- Use `recent_discussions` to enrich practical examples.

4. Quality gates
- Ensure `master_document` is non-empty and markdown-valid-ish.
- Ensure `structure_outline` and `core_arguments` are non-empty lists.
- Keep deterministic ordering in returned arrays.

5. Contract validation before return
- Validate against `MasterContentResponse` before returning.

## Safe Improvement Areas

- Better LLM prompts for audience/tone/depth alignment.
- Multi-pass generation (draft + refinement) inside Node 2.
- Stronger fallback behavior when LLM/API calls fail.
- Deterministic markdown formatting conventions.
- Light scoring/quality checks before final output.

## Avoid These Breaking Changes

- Renaming/removing output keys.
- Returning nested objects instead of list[str] for outline/arguments.
- Writing master result somewhere other than `context.state["master"]`.
- Depending on fields not guaranteed by Node 0/Node 1 contracts.

## Testing Checklist

Minimum:
- Node 2 returns contract-valid output for normal inputs.
- Node 2 returns contract-valid output on degraded/missing research inputs.
- Node 3 still works against Node 2 output with no code changes.

Recommended tests to add:
- Unit test: deterministic section ordering.
- Unit test: fallback generation with missing `research_summary`.
- Contract validation test for Node 2 output shape.

## Done Criteria for Node 2 Owner

- Logic is improved but output contract is unchanged.
- `master_document`, `structure_outline`, `core_arguments` are always valid.
- Node 3/editorial and adapters continue working unchanged.
- Failure paths still produce usable, contract-valid master content.
