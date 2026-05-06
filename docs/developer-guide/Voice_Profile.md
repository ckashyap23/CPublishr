# Voice Profiles

Voice profiles store reusable tone and style guidance derived from a user's content datasets.

## Main Files

| Layer | File |
|-------|------|
| API endpoints | `backend/src/api/v1/endpoints/voice_profiles.py` |
| Schemas | `backend/src/schemas/voice_profiles.py` |
| Service | `backend/src/services/voice_profiles/service.py` |
| Models | `backend/src/db/models/voice_profile.py` |
| Repositories | `backend/src/db/repositories/voice_profile_module_repository.py` |

## Runtime Surface

Routes are under:

```text
/api/v1/voice-profiles
```

Core operations:

- create/list/get collections
- add datasets
- create/list/get profiles
- generate profile versions
- activate versions
- update profile/version status
- delete profiles

## Data Model

| Table | Purpose |
|-------|---------|
| `voice_profile_collections` | Named user-owned profile collection |
| `voice_profiles` | Profile records within a collection |
| `voice_profile_datasets` | Dataset metadata and blob/source references |
| `voice_profile_versions` | Generated versioned profile JSON and status |
| `voice_profile_version_datasets` | Dataset lineage for each version |
| `dataset_entries` | Individual normalized source entries |

Generated versions include:

- `core_voice`
- `style_summary`
- `tone_baseline`
- `do_rules`
- `dont_rules`
- `raw_profile_json`
- status and activation fields

## Provider Notes

Dataset ingestion currently reads Azure Blob paths configured by:

- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_PROFILE_ENTRIES_CONTAINER`

LLM generation uses the shared text LLM provider settings:

- `LLM_PROVIDER=azure`
- `LLM_PROVIDER=openai`

If the LLM path fails, the service falls back to conservative profile JSON.

## Downstream Usage

An active profile can be referenced from project context through `voice_profile_id`.

The default fallback profile ID is:

```text
__default_voice_profile__
```

Use the default profile when users have not configured a custom dataset-backed profile.

## Implementation Rules

- Keep generated profile JSON backward-compatible for downstream prompt builders.
- Preserve dataset lineage when generating a new version.
- Do not activate rejected or failed versions.
- Treat source blob/data access errors as user-visible validation failures.
- Keep service logic separate from API schema definitions.

## Test Checklist

- Create collection/profile.
- Add dataset metadata.
- Generate a version with valid lineage.
- Activate one version and ensure older active versions are deactivated as needed.
- Verify fallback/default profile behavior.
