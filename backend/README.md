# Backend

Run locally:

```powershell
cd backend
.\scripts\bootstrap.ps1
uvicorn src.main:app --reload
```

## Node 0 (Topic Initialization) Request Contract

Required fields:
- `project_id`
- `topic_title`
- `core_idea`
- `tone_preference`
- `distribution_targets`

Optional fields:
- `user_content`
- `target_audience`
- `content_depth`
