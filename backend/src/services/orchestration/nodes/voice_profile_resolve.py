from __future__ import annotations

import logging
import uuid
from typing import Any

from src.db.repositories.voice_profile_module_repository import VoiceProfileModuleRepository
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode

logger = logging.getLogger(__name__)


class VoiceProfileResolveNode(OrchestrationNode):
    """
    Resolves a user-selected voice profile version and stores compact voice guidance in:
      context.state["voice_profile"]

    Rules:
    - If context_bundle has no voice_profile_id, do nothing and clear stale voice state.
    - Resolve in priority order: active -> latest approved.
    - Never cross user boundaries (repository is user-scoped).
    """

    name = "voice_profile_resolve"

    def __init__(self, repo: VoiceProfileModuleRepository):
        self.repo = repo

    @staticmethod
    def _normalize_voice_profile_id(value: Any) -> str:
        s = str(value or "").strip()
        if not s or s.lower() in {"(none)", "none", "null", "not specified"}:
            return ""
        return s

    @staticmethod
    def _extract_exemplars(raw_profile_json: Any, style_summary: Any) -> list[dict]:
        exemplars: list[dict] = []

        if isinstance(raw_profile_json, dict):
            raw_exemplars = raw_profile_json.get("exemplars")
            if isinstance(raw_exemplars, list):
                for item in raw_exemplars:
                    if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
                        exemplars.append(
                            {
                                "text": item["text"].strip()[:200],
                                "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
                            }
                        )
                    elif isinstance(item, str) and item.strip():
                        exemplars.append({"text": item.strip()[:200], "tags": []})

        if not exemplars and isinstance(style_summary, dict):
            style_exemplars = style_summary.get("exemplars")
            if isinstance(style_exemplars, list):
                for item in style_exemplars:
                    if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
                        exemplars.append(
                            {
                                "text": item["text"].strip()[:200],
                                "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
                            }
                        )

        return exemplars[:4]

    def _select_version(self, versions):
        if not versions:
            return None
        active = next((v for v in versions if bool(v.is_active)), None)
        if active is not None:
            return active
        approved = next((v for v in versions if str(v.generation_status or "").strip().lower() == "approved"), None)
        return approved

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        bundle = context.state.get("context_bundle") or {}
        voice_profile_id = self._normalize_voice_profile_id(bundle.get("voice_profile_id"))

        if not voice_profile_id:
            context.state.pop("voice_profile", None)
            return NodeExecutionResult(
                status="completed",
                output_payload={"resolved": False, "reason": "no_voice_profile_id_provided"},
            )

        try:
            profile_uuid = uuid.UUID(voice_profile_id)
        except ValueError:
            context.state.pop("voice_profile", None)
            return NodeExecutionResult(
                status="completed",
                output_payload={
                    "resolved": False,
                    "reason": "invalid_voice_profile_id",
                    "voice_profile_id": voice_profile_id,
                },
            )

        voice_profile = self.repo.get_voice_profile(profile_uuid)
        if voice_profile is None:
            context.state.pop("voice_profile", None)
            return NodeExecutionResult(
                status="completed",
                output_payload={
                    "resolved": False,
                    "reason": "not_found",
                    "voice_profile_id": voice_profile_id,
                },
            )

        versions = self.repo.list_versions(profile_uuid)
        selected = self._select_version(versions)
        if selected is None:
            context.state.pop("voice_profile", None)
            return NodeExecutionResult(
                status="completed",
                output_payload={
                    "resolved": False,
                    "reason": "no_active_or_approved_version",
                    "voice_profile_id": voice_profile_id,
                },
            )

        style_summary = selected.style_summary if isinstance(selected.style_summary, dict) else {}
        raw_profile_json = selected.raw_profile_json if isinstance(selected.raw_profile_json, dict) else {}
        resolved_payload = {
            "voice_profile_id": str(voice_profile.voice_profile_id),
            "voice_profile_version_id": str(selected.voice_profile_version_id),
            "voice_profile_name": str(voice_profile.voice_profile_name),
            "version_no": int(selected.version_no),
            "generation_status": str(selected.generation_status or ""),
            "core_voice": str(selected.core_voice or "not specified"),
            "style_summary": style_summary,
            "tone_baseline": selected.tone_baseline if isinstance(selected.tone_baseline, dict) else {},
            "do_rules": [str(x).strip() for x in (selected.do_rules or []) if str(x).strip()],
            "dont_rules": [str(x).strip() for x in (selected.dont_rules or []) if str(x).strip()],
            "exemplars": self._extract_exemplars(raw_profile_json, style_summary),
        }

        context.state["voice_profile"] = resolved_payload
        return NodeExecutionResult(
            status="completed",
            output_payload={
                "resolved": True,
                "voice_profile_id": resolved_payload["voice_profile_id"],
                "voice_profile_version_id": resolved_payload["voice_profile_version_id"],
                "version_no": resolved_payload["version_no"],
                "generation_status": resolved_payload["generation_status"],
            },
        )
