# Contracts

Source of truth: `backend/src/contracts/prd.py`
Examples: `backend/contracts/examples/*.json`
Validation: `backend/tests/unit/test_prd_contract_examples.py`

## Node 0 TopicInitializationRequest (Current)

Required:
- `project_id: str`
- `topic_title: str`
- `core_idea: str`
- `tone_preference: "professional" | "analytical" | "conversational"`
- `distribution_targets: list[...]`

Optional:
- `user_content: str | None`
- `target_audience: "builders" | "founders" | "enterprise" | "general tech" | None`
- `content_depth: "surface" | "intermediate" | "deep" | None`
