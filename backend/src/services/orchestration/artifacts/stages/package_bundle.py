from __future__ import annotations

from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext, StageResult


class PackageBundleStage:
    name = "package"

    def run(self, ctx: PipelineContext) -> StageResult:
        if "bundle" not in ctx.requested_formats:
            return StageResult(stage=self.name, drafts=[])

        refs = []
        seq = 1
        for stage_name, drafts in ctx.stage_outputs.items():
            if stage_name == self.name:
                continue
            for d in drafts:
                refs.append(
                    {
                        "item_type": "artifact_ref",
                        "sequence": seq,
                        "meta": {"format": d.format, "role": d.format},
                    }
                )
                seq += 1

        payload = default_payload_template()
        payload["items"] = refs
        draft = ArtifactDraft(
            format="bundle",
            title=f"{ctx.topic_title} - Bundle",
            payload_json=payload,
            tags_json=list(ctx.seed_keywords),
        )
        return StageResult(stage=self.name, drafts=[draft])