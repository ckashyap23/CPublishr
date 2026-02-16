from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode

logger = logging.getLogger(__name__)


@dataclass
class VariantSpec:
    id: str
    label: str
    weight_user: float
    weight_research: float
    structure: str  # narrative_first | framework_first | problem_solution | faq | playbook | contrarian_take


class MasterContentNode(OrchestrationNode):
    name = "master_content"

    def __init__(self, llm: Optional[AzureOpenAIClient] = None):
        self.llm = llm

    @staticmethod
    def _extract_section_map(document: str, fallback: list[str]) -> list[str]:
        headings: list[str] = []
        for line in (document or "").splitlines():
            s = line.strip()
            if not s.startswith("## "):
                continue
            heading = s[3:].strip()
            if heading and heading not in headings:
                headings.append(heading)
        return headings or list(fallback)

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        b: Dict[str, Any] = context.state.get("context_bundle") or {}
        r: Dict[str, Any] = context.state.get("research") or {}

        title = (b.get("topic_title") or "AI Topic").strip()
        core = (b.get("core_idea") or "One idea, many platform formats.").strip()
        user_content = (b.get("user_content") or "").strip()

        # Audience inputs (used as generation constraints; do not emit in contract output)
        target_audience = (b.get("target_audience") or "general").strip()
        content_depth = (b.get("content_depth") or "intermediate").strip()
        tone_preference = (b.get("tone_preference") or "professional").strip()

        research_summary = (r.get("research_summary") or "").strip()

        variants: List[VariantSpec] = [
            VariantSpec("v_user70_narrative", "User-led narrative (70/30) - Narrative-first", 0.7, 0.3, "narrative_first"),
            VariantSpec("v_research70_framework", "Research-led authority (30/70) - Framework-first", 0.3, 0.7, "framework_first"),
            VariantSpec("v_balanced_problem_solution", "Balanced (50/50) - Problem/Solution", 0.5, 0.5, "problem_solution"),
            VariantSpec("v_balanced_faq", "Balanced (50/50) - FAQ format", 0.5, 0.5, "faq"),
            VariantSpec("v_balanced_playbook", "Balanced (50/50) - Playbook format", 0.5, 0.5, "playbook"),
            VariantSpec("v_balanced_contrarian", "Balanced (50/50) - Contrarian take", 0.5, 0.5, "contrarian_take"),
        ]

        user_section = f"## User Content Input\n{user_content}\n\n" if user_content else ""
        default_section_map = ["Hook", "Core Idea", "Section 1", "Section 2", "Section 3", "Key Takeaways", "Close"]
        fallback_master = (
            f"# {title}\n\n"
            "## Hook\n"
            "not specified\n\n"
            f"## Core Idea\n{core}\n\n"
            f"{user_section}"
            "## Section 1\n"
            f"{(research_summary or 'not specified')}\n\n"
            "## Section 2\n"
            "not specified\n\n"
            "## Section 3\n"
            "not specified\n\n"
            "## Key Takeaways\n"
            "- not specified\n- not specified\n- not specified\n- not specified\n- not specified\n\n"
            "## Close\n"
            "not specified\n"
        ).strip()

        out: Dict[str, Any] = {
            "master_document": fallback_master,
            "structure_outline": self._extract_section_map(fallback_master, default_section_map),
            "core_arguments": ["not specified"],
            "variants": [],
        }

        if self.llm and self.llm.enabled:
            # Generate BASE first (small, parseable JSON), then generate each variant in separate calls.
            base_system_prompt = f"""
You are an expert editorial writer generating canonical long-form content.

Audience constraints (MUST apply):
- target_audience: {target_audience}
- content_depth: {content_depth}
- tone_preference: {tone_preference}

Hard constraints (must follow):
- No new facts beyond the provided research_summary.
- If something is unknown or not provided, write "not specified".
- Maintain the core idea unchanged in meaning.
- Every document MUST include: Hook, exactly 3 H2 sections, exactly 5 bullets total, and a Close.
- Return STRICT JSON only. No markdown fences. No commentary. No extra keys.
""".strip()

            base_user_prompt = f"""
Return STRICT JSON with this schema EXACTLY:
{{
  "master_document": "<markdown>",
  "structure_outline": ["<base_section_heading>", "..."],
  "core_arguments": ["<keyword_or_short_phrase>", "..."]
}}

Inputs:
- title: {title}
- core_idea (keep meaning unchanged): {core}
- target_audience: {target_audience}
- content_depth: {content_depth}
- tone_preference: {tone_preference}
- user_content: {user_content if user_content else "not specified"}
- research_summary (facts source; do not add facts beyond this): {research_summary if research_summary else "not specified"}

What to generate:
- BASE master_document: canonical markdown based on inputs and audience constraints.
- core_arguments: extract 10-20 critical keywords/short phrases from the BASE master_document.
- structure_outline: the H2 headings in order.
""".strip()

            try:
                raw = self.llm.chat(
                    system_prompt=base_system_prompt,
                    user_prompt=base_user_prompt,
                    temperature=0.4,
                    max_tokens=2500,
                )
                parsed = parse_json_object(raw)
                if not parsed:
                    logger.warning("MasterContentNode: base LLM output was not parseable JSON; using fallback.")
                else:
                    base_document = str(parsed.get("master_document") or fallback_master)
                    structure_outline = parsed.get("structure_outline")
                    if isinstance(structure_outline, list) and structure_outline:
                        base_outline = [str(x) for x in structure_outline]
                    else:
                        base_outline = self._extract_section_map(base_document, default_section_map)

                    core_arguments = parsed.get("core_arguments")
                    if not isinstance(core_arguments, list) or not core_arguments:
                        core_arguments = ["not specified"]

                    out = {
                        "master_document": base_document,
                        "structure_outline": base_outline,
                        "core_arguments": [str(x) for x in core_arguments],
                        "variants": [],
                    }

                    # Now generate each variant separately (avoids giant JSON/truncation).
                    for spec in variants:
                        variant_user_prompt = f"""
Return STRICT JSON with this schema EXACTLY:
{{
  "label": "<string>",
  "levers": {{
    "weight_user": <number>,
    "weight_research": <number>,
    "structure": "<narrative_first|framework_first|problem_solution|faq|playbook|contrarian_take>"
  }},
  "master_document": "<markdown>",
  "structure_outline": ["<variant_section_heading>", "..."]
}}

Variant spec:
- label: {spec.label}
- levers: weight_user={spec.weight_user}, weight_research={spec.weight_research}, structure={spec.structure}

Inputs:
- title: {title}
- core_idea (keep meaning unchanged): {core}
- target_audience: {target_audience}
- content_depth: {content_depth}
- tone_preference: {tone_preference}
- user_content: {user_content if user_content else "not specified"}
- research_summary (facts source; do not add facts beyond this): {research_summary if research_summary else "not specified"}

Formatting rules:
- Include a Hook section.
- Include exactly 3 main sections (H2 headings).
- Include exactly 5 bullets total (one bullet list with 5 items).
- End with a Close section.

Remember: No new facts beyond research_summary. Unknown -> "not specified". Core idea meaning unchanged.
""".strip()

                        try:
                            v_raw = self.llm.chat(
                                system_prompt=base_system_prompt,
                                user_prompt=variant_user_prompt,
                                temperature=0.4,
                                max_tokens=2000,
                            )
                            v_parsed = parse_json_object(v_raw)
                            if not v_parsed:
                                logger.warning("MasterContentNode: variant LLM output not parseable JSON; skipping variant.")
                                continue
                            out["variants"].append(
                                {
                                    "id": spec.id,
                                    "label": str(v_parsed.get("label") or spec.label),
                                    "levers": {
                                        "weight_user": float((v_parsed.get("levers") or {}).get("weight_user") or spec.weight_user),
                                        "weight_research": float((v_parsed.get("levers") or {}).get("weight_research") or spec.weight_research),
                                        "structure": str((v_parsed.get("levers") or {}).get("structure") or spec.structure),
                                    },
                                    "master_document": str(v_parsed.get("master_document") or ""),
                                    "structure_outline": [str(x) for x in (v_parsed.get("structure_outline") or [])],
                                }
                            )
                        except Exception:
                            logger.exception("MasterContentNode: variant generation failed; skipping variant.")
                            continue
            except Exception:
                logger.exception("MasterContentNode: base generation failed; using fallback.")

        contract_out = {
            "master_document": str(out.get("master_document") or fallback_master),
            "structure_outline": [str(x) for x in (out.get("structure_outline") or self._extract_section_map(fallback_master, default_section_map))],
            "core_arguments": [str(x) for x in (out.get("core_arguments") or ["not specified"])],
            "master_variants": [],
        }
        for variant in out.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            label = str(variant.get("label") or "").strip()
            document = str(variant.get("master_document") or "").strip()
            if not label or not document:
                continue
            variant_outline = variant.get("structure_outline")
            if isinstance(variant_outline, list) and variant_outline:
                normalized_outline = [str(x) for x in variant_outline]
            else:
                normalized_outline = self._extract_section_map(document, contract_out["structure_outline"])
            contract_out["master_variants"].append(
                {
                    "label": label,
                    "master_document": document,
                    "structure_outline": normalized_outline,
                    "core_arguments": list(contract_out["core_arguments"]),
                }
            )
        context.state["master"] = contract_out
        return NodeExecutionResult(status="completed", output_payload=contract_out)
