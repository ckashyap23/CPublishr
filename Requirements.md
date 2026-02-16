# AI Multi-Agent Content Orchestration & Publishing Platform

## PRD (Recovered Summary)

Core workflow:
1. Node 0: Topic Initialization
2. Node 1: Research & Trend Intelligence
3. Node 2: Master Content Generator
4. Node 3: Editorial (Human-in-the-loop)

Node 0 input contract:
- Required: `topic_title`, `core_idea`, `tone_preference`, `distribution_targets`
- Optional: `user_content`, `target_audience`, `content_depth`

Platform adapters:
- LinkedIn, X, YouTube, Instagram, Substack, Medium, GitHub

Storage tracks:
- Project
- ContentVersion
- PlatformOutput
- Publishing jobs

Distribution:
- OAuth and scheduling are future stages; MVP uses publish stub while preserving contracts.

Design principles:
- Same idea, different packaging.
- Layered AI architecture.
- Contract-first integration between components.
