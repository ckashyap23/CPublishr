from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.services.llm.azure_openai import AzureOpenAIClient, parse_json_object
from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult
from src.services.orchestration.nodes.base import OrchestrationNode

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Deterministic editorial playbooks (internal guidance only)
# -----------------------------------------------------------------------------

STRUCTURED_HEADINGS: List[str] = [
    "Hook",
    "Core Idea",
    "Section 1",
    "Section 2",
    "Section 3",
    "Key Takeaways",
    "Close",
]

AUDIENCE_PLAYBOOK: Dict[str, Dict[str, str]] = {
    "general": {
        "assumptions": "Assume a broad audience; explain terms in plain English.",
        "style": "Concrete, clear, minimal jargon, avoid fluff.",
        "examples": "Use relatable examples and simple analogies.",
    },
    "professionals": {
        "assumptions": "Assume workplace context and limited time.",
        "style": "Crisp, practical, executive-friendly clarity.",
        "examples": "Work scenarios, decision framing, tradeoffs.",
    },
    "creators": {
        "assumptions": "Assume attention is scarce; prioritize hooks and clarity.",
        "style": "Engaging, punchy, vivid phrasing without being cringe.",
        "examples": "Audience-first framing, pattern examples, quick wins.",
    },
    "smb": {
        "assumptions": "Assume ROI-focus and limited bandwidth.",
        "style": "Direct, outcome-oriented, actionable steps.",
        "examples": "Time/cost savings, simple implementation path.",
    },
    "founders": {
        "assumptions": "Assume fast decisions and outcome accountability.",
        "style": "Direct, ROI framing, risks/tradeoffs, strong POV.",
        "examples": "Time-to-value, adoption, positioning, iteration loops.",
    },
    "builders": {
        "assumptions": "Assume technical curiosity; skip basics when possible.",
        "style": "Precise, practical, tradeoffs, edge-case aware.",
        "examples": "Constraints, implementation steps, decision tradeoffs.",
    },
    "marketing": {
        "assumptions": "Assume goals/metrics mindset and audience psychology awareness.",
        "style": "Clear positioning, persuasion with substance.",
        "examples": "Messaging, funnel, experiments, creative angles.",
    },
    "sales": {
        "assumptions": "Assume objection-handling and value articulation matters.",
        "style": "Benefit-led, customer pain aware, concise.",
        "examples": "Objections, use cases, proof cues.",
    },
    "enterprise": {
        "assumptions": "Assume governance, compliance, scale, multi-stakeholder environment.",
        "style": "Structured, risk-aware, measurable outcomes.",
        "examples": "Operating model, controls, rollout, change management.",
    },
}

GOAL_PLAYBOOK: Dict[str, Dict[str, str]] = {
    "educate": {
        "opening": "Teach with clarity; define terms; use progressive reveal.",
        "close": "Invite questions or ask for readers’ examples.",
    },
    "thought_leadership": {
        "opening": "Strong thesis + clear POV; acknowledge tradeoffs.",
        "close": "Ask a sharp question to drive thoughtful comments.",
    },
    "promote": {
        "opening": "Problem-first; empathize; show value without hype.",
        "close": "Clear CTA with a low-friction next step.",
    },
    "entertain": {
        "opening": "Light hook; keep pace fast; be witty but not forced.",
        "close": "Playful prompt for reactions/shares.",
    },
    "recruit": {
        "opening": "Mission + reality; highlight what’s unique.",
        "close": "Invite DMs/applications with specifics.",
    },
    "community": {
        "opening": "Shared identity and inclusive framing.",
        "close": "Ask readers to add examples/resources.",
    },
    "convert": {
        "opening": "Pain → benefit; clear stakes; be direct.",
        "close": "Direct CTA; remove ambiguity; state who it’s for.",
    },
}

STANCE_PLAYBOOK: Dict[str, str] = {
    "neutral": "Present multiple perspectives; avoid strong claims unless supported.",
    "supportive": "Advocate clearly; briefly acknowledge a reasonable counterpoint.",
    "contrarian": "Challenge the default view; be fair; pre-empt objections.",
    "balanced": "Show both sides then land on a clear conclusion.",
}

DETAIL_LEVEL_PLAYBOOK: Dict[str, str] = {
    "quick_take": "Keep it concise; emphasize takeaway over nuance.",
    "practical": "Practical depth; include examples; include tradeoffs.",
    "deep_dive": "Add nuance, caveats, and examples; address common objections.",
}

AUDIENCE_FAMILIARITY_PLAYBOOK: Dict[str, str] = {
    "new": "Define terms; avoid jargon; use analogies; explain the 'why'.",
    "somewhat_familiar": "Assume basics; focus on the 'how' and tradeoffs.",
    "very_familiar": "Skip basics; focus on nuance, edge cases, and non-obvious insights.",
}


# -----------------------------------------------------------------------------
# Variants (output contract unchanged)
# -----------------------------------------------------------------------------

@dataclass
class VariantSpec:
    id: str
    label: str
    weight_user: float
    weight_research: float
    structure: str  # narrative_first | framework_first | problem_solution | faq | playbook | contrarian_take


# -----------------------------------------------------------------------------
# Node
# -----------------------------------------------------------------------------

class MasterContentNode(OrchestrationNode):
    """
    Generates canonical platform-agnostic master content using:
    - context_bundle (user inputs + constraints)
    - research schema outputs

    Output contract is preserved:
      {
        "master_document": str,
        "structure_outline": list[str],
        "core_arguments": list[str],
        "master_variants": list[{label, master_document, structure_outline, core_arguments}]
      }

    Note: artifact agents use entire master_document + core_arguments.
    Therefore, structure is a QUALITY tool (conditional) rather than a dependency.
    """

    name = "master_content"

    def __init__(self, llm: Optional[AzureOpenAIClient] = None):
        self.llm = llm

    # ----------------------------
    # Utilities
    # ----------------------------

    @staticmethod
    def _extract_markdown_h2_headings(document: str) -> List[str]:
        headings: List[str] = []
        for line in (document or "").splitlines():
            s = line.strip()
            if s.startswith("## "):
                h = s[3:].strip()
                if h:
                    headings.append(h)
        return headings

    @staticmethod
    def _normalize_constraints(raw: Any) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            return {"must_include": [], "must_avoid": [], "forbidden_claims": []}
        out = dict(raw)
        for k in ("must_include", "must_avoid", "forbidden_claims"):
            v = out.get(k)
            if isinstance(v, list):
                out[k] = [str(x).strip() for x in v if str(x).strip()]
            elif isinstance(v, str) and v.strip():
                out[k] = [v.strip()]
            else:
                out[k] = []
        return out

    @staticmethod
    def _normalize_enum(value: Any, allowed: List[str], default: str) -> str:
        s = str(value or "").strip().lower()
        return s if s in allowed else default

    @staticmethod
    def _get_audience_inputs(b: Dict[str, Any]) -> Tuple[str, str]:
        """
        Supports:
          target_audience as dict {primary_segment, notes}
          OR as str
        """
        aud_in = b.get("target_audience")
        audience = ""
        notes = ""

        if isinstance(aud_in, str):
            audience = aud_in.strip()
        elif isinstance(aud_in, dict):
            audience = str(aud_in.get("primary_segment") or "").strip()
            notes = str(aud_in.get("notes") or "").strip()

        a = (audience or "general").strip().lower()

        # Common aliases -> playbook keys
        aliases = {
            # New schema values
            "creators_influencers": "creators",
            "small_business_owners": "smb",
            "founders_entrepreneurs": "founders",
            "builders_developers": "builders",
            "marketing_growth": "marketing",
            "sales_partnerships": "sales",
            "enterprise_leaders": "enterprise",
            "other": "general",
            # Legacy values / loose inputs
            "creator": "creators",
            "influencer": "creators",
            "influencers": "creators",
            "content creators": "creators",
            "small_business": "smb",
            "small business": "smb",
            "business_owner": "smb",
            "business owners": "smb",
            "developer": "builders",
            "developers": "builders",
            "engineers": "builders",
            "tech": "builders",
            "marketer": "marketing",
            "marketers": "marketing",
            "sales / partnerships": "sales",
            "sales & partnerships": "sales",
            "enterprise leaders": "enterprise",
            "enterprise decision makers": "enterprise",
            "white collar": "professionals",
            "professional": "professionals",
            "professionals": "professionals",
        }
        a = aliases.get(a, a)
        if a not in AUDIENCE_PLAYBOOK:
            a = "general"

        return a, (notes or "not specified")

    @staticmethod
    def _format_research_context(r: Dict[str, Any]) -> str:
        """
        Packs research schema into a single string for model grounding.
        Keeps your research logic the same; just makes it easier for the LLM to use.
        """
        def _as_list(key: str) -> List[str]:
            v = r.get(key)
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            return []

        summary = str(r.get("research_summary") or "").strip() or "not specified"
        emerging_tools = _as_list("emerging_tools")
        recent_discussions = _as_list("recent_discussions")
        key_insights = _as_list("key_insights")
        contrarian_angles = _as_list("contrarian_angles")

        lines: List[str] = []
        lines.append("Research Summary:")
        lines.append(summary)

        if key_insights:
            lines.append("\nKey Insights:")
            for x in key_insights[:12]:
                lines.append(f"- {x}")

        if contrarian_angles:
            lines.append("\nContrarian Angles:")
            for x in contrarian_angles[:10]:
                lines.append(f"- {x}")

        if recent_discussions:
            lines.append("\nRecent Discussions:")
            for x in recent_discussions[:10]:
                lines.append(f"- {x}")

        if emerging_tools:
            lines.append("\nEmerging Tools:")
            for x in emerging_tools[:12]:
                lines.append(f"- {x}")

        return "\n".join(lines).strip()

    @staticmethod
    def _build_editorial_brief(
        target_audience: str,
        target_audience_notes: str,
        audience_familiarity: str,
        detail_level: str,
        tone_preference: str,
        stance: str,
        primary_goal: str,
        desired_action: str,
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        a = AUDIENCE_PLAYBOOK.get(target_audience, AUDIENCE_PLAYBOOK["general"])
        goal = GOAL_PLAYBOOK.get(primary_goal, {})

        return {
            "audience": {
                "segment": target_audience,
                "notes": target_audience_notes,
                "assumptions": a["assumptions"],
                "style": a["style"],
                "examples": a["examples"],
                "audience_familiarity_guidance": AUDIENCE_FAMILIARITY_PLAYBOOK.get(
                    audience_familiarity, AUDIENCE_FAMILIARITY_PLAYBOOK["somewhat_familiar"]
                ),
            },
            "detail_level_guidance": DETAIL_LEVEL_PLAYBOOK.get(detail_level, DETAIL_LEVEL_PLAYBOOK["practical"]),
            "tone": tone_preference,
            "stance_guidance": STANCE_PLAYBOOK.get(stance, STANCE_PLAYBOOK["balanced"]),
            "goal_guidance": {
                "primary_goal": primary_goal,
                "opening": goal.get("opening", "Start strong and stay clear."),
                "close": goal.get("close", "End with a clear takeaway."),
            },
            "cta": {
                "desired_action": desired_action,
                "instruction": (
                    "End with a single-line CTA aligned to desired_action. "
                    "If desired_action is 'not specified', end with a thoughtful question."
                ),
            },
            "constraints": constraints,
        }

    @staticmethod
    def _choose_structure_policy(primary_goal: str, detail_level: str, tone_preference: str) -> str:
        """
        Returns: "structured" | "freeform"

        Intent:
        - structured helps clarity and repurposability for education/authority/promo
        - freeform helps entertainment/informal content
        """
        g = (primary_goal or "").strip().lower()
        d = (detail_level or "").strip().lower()
        t = (tone_preference or "").strip().lower()

        if g == "entertain":
            return "freeform"

        # If explicitly shallow + playful, allow freeform
        playful = any(x in t for x in ("witty", "fun", "casual", "playful", "humor", "humorous", "informal"))
        if d == "quick_take" and playful:
            return "freeform"

        # Otherwise default to structured (better for quality + reuse)
        return "structured"

    @staticmethod
    def _is_compliant_structured(doc: str) -> bool:
        """
        Checks compliance only for STRUCTURED mode.
        """
        if not doc or not isinstance(doc, str):
            return False

        found = [line.strip()[3:].strip() for line in doc.splitlines() if line.strip().startswith("## ")]
        if found != STRUCTURED_HEADINGS:
            return False

        in_takeaways = False
        bullets = 0
        for line in doc.splitlines():
            if line.strip() == "## Key Takeaways":
                in_takeaways = True
                continue
            if line.strip().startswith("## ") and in_takeaways:
                break
            if in_takeaways and line.strip().startswith("- "):
                bullets += 1
        return bullets == 5

    def _repair_structured(
        self,
        bad_doc: str,
        core_idea: str,
        editorial_brief: Dict[str, Any],
        research_context: str,
        title: str,
    ) -> str:
        """
        Repairs STRUCTURED markdown to meet heading/bullet rules.
        Only used when policy == structured.
        """
        if not (self.llm and self.llm.enabled):
            return bad_doc

        repair_system = "You are an editorial formatter. Fix structure without changing meaning."
        repair_user = f"""
Fix the document to comply with rules. Keep meaning the same. Do not add new facts.

Rules:
- Headings exactly in this order (no extra headings), each with '## ':
  {STRUCTURED_HEADINGS}
- Exactly 5 bullets under '## Key Takeaways'.
- First sentence under '## Core Idea' must preserve meaning of: {core_idea}
- Do NOT invent statistics, named entities, or factual claims not supported by research_context.
  If something is unknown, write "not specified".
- Respect constraints in editorial brief.

Editorial brief:
{editorial_brief}

Facts source (do not go beyond this):
{research_context}

Return ONLY the corrected markdown (no JSON, no commentary).

Title: {title}

Document to fix:
{bad_doc}
""".strip()

        fixed = self.llm.chat(
            system_prompt=repair_system,
            user_prompt=repair_user,
            temperature=0.1,
            max_tokens=2200,
        )
        return (fixed or bad_doc).strip()

    @staticmethod
    def _derive_outline_freeform(document: str) -> List[str]:
        """
        For freeform content:
        - Prefer H2 headings if present.
        - Else return minimal beats.
        """
        h2s = MasterContentNode._extract_markdown_h2_headings(document)
        if h2s:
            # Use up to 10 headings to avoid huge outlines
            return [str(x) for x in h2s[:10]]

        # Lightweight beat fallback
        return ["Hook", "Body", "Close"]

    @staticmethod
    def _variant_directive(spec: VariantSpec, stance: str, primary_goal: str, desired_action: str) -> str:
        bits: List[str] = []

        if spec.structure == "contrarian_take" or stance == "contrarian":
            bits.append("Emphasize counter-intuition and pre-empt objections fairly.")

        if primary_goal == "entertain" and spec.structure == "narrative_first":
            bits.append("Keep it witty/light while staying coherent and respectful.")

        if desired_action in ("comment", "share"):
            bits.append("End with a single engaging question.")

        if not bits:
            bits.append("Keep it clear, tight, and audience-aligned.")

        return " ".join(bits)

    @staticmethod
    def _effective_weights(user_content: str, w_user: float, w_research: float) -> Tuple[float, float]:
        if not user_content.strip():
            return 0.0, 1.0
        total = max(w_user + w_research, 1e-6)
        return w_user / total, w_research / total

    @staticmethod
    def _fallback_master_structured(title: str, core: str, user_content: str, research_context: str) -> str:
        uc = user_content.strip() or "not specified"
        rc = research_context.strip() or "not specified"
        return (
            f"# {title}\n\n"
            "## Hook\n"
            "not specified\n\n"
            "## Core Idea\n"
            f"{core}\n\n"
            "## Section 1\n"
            f"{uc}\n\n"
            "## Section 2\n"
            f"{rc}\n\n"
            "## Section 3\n"
            "not specified\n\n"
            "## Key Takeaways\n"
            "- not specified\n"
            "- not specified\n"
            "- not specified\n"
            "- not specified\n"
            "- not specified\n\n"
            "## Close\n"
            "not specified\n"
        ).strip()

    @staticmethod
    def _fallback_master_freeform(title: str, core: str, user_content: str, research_context: str) -> str:
        uc = user_content.strip() or "not specified"
        rc = research_context.strip() or "not specified"
        return (
            f"# {title}\n\n"
            f"{core}\n\n"
            f"{uc}\n\n"
            f"{rc}\n\n"
            "Close: not specified\n"
        ).strip()

    @staticmethod
    def _fallback_core_arguments(title: str, core: str) -> List[str]:
        # Safe minimal fallback
        bits = []
        if title.strip():
            bits.append(title.strip())
        if core.strip():
            bits.append(core.strip())
        return bits[:5] if bits else ["not specified"]

    # ----------------------------
    # Main run
    # ----------------------------

    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        b: Dict[str, Any] = context.state.get("context_bundle") or {}
        r: Dict[str, Any] = context.state.get("research") or {}

        title = (b.get("topic_title") or "AI Topic").strip()
        core = (b.get("core_idea") or "One idea, many platform formats.").strip()
        user_content = (b.get("user_content") or "").strip()

        # Audience inputs (constraints only; not emitted in output contract)
        target_audience, target_audience_notes = self._get_audience_inputs(b)

        # Normalize enums so prompts are deterministic
        audience_familiarity = self._normalize_enum(
            b.get("audience_familiarity"),
            ["new", "somewhat_familiar", "very_familiar"],
            "somewhat_familiar",
        )
        detail_level = self._normalize_enum(
            b.get("detail_level"),
            ["quick_take", "practical", "deep_dive"],
            "practical",
        )
        tone_preference = str(b.get("tone_preference") or "professional").strip()
        stance = self._normalize_enum(b.get("stance"), ["neutral", "supportive", "contrarian", "balanced"], "balanced")

        primary_goal = str(b.get("primary_goal") or "not specified").strip().lower()
        desired_action = str(b.get("desired_action") or "not specified").strip().lower()

        voice_profile_id = str(b.get("voice_profile_id") or "not specified").strip()  # placeholder only
        constraints = self._normalize_constraints(b.get("constraints"))

        research_context = self._format_research_context(r)

        structure_policy = self._choose_structure_policy(primary_goal, detail_level, tone_preference)

        variants: List[VariantSpec] = [
            VariantSpec("v_user70_narrative", "User-led narrative (70/30) - Narrative-first", 0.7, 0.3, "narrative_first"),
            VariantSpec("v_research70_framework", "Research-led authority (30/70) - Framework-first", 0.3, 0.7, "framework_first"),
            VariantSpec("v_balanced_problem_solution", "Balanced (50/50) - Problem/Solution", 0.5, 0.5, "problem_solution"),
            VariantSpec("v_balanced_faq", "Balanced (50/50) - FAQ format", 0.5, 0.5, "faq"),
            VariantSpec("v_balanced_playbook", "Balanced (50/50) - Playbook format", 0.5, 0.5, "playbook"),
            VariantSpec("v_balanced_contrarian", "Balanced (50/50) - Contrarian take", 0.5, 0.5, "contrarian_take"),
        ]

        if structure_policy == "structured":
            fallback_master = self._fallback_master_structured(title, core, user_content, research_context)
            fallback_outline = STRUCTURED_HEADINGS[:]
        else:
            fallback_master = self._fallback_master_freeform(title, core, user_content, research_context)
            fallback_outline = self._derive_outline_freeform(fallback_master)

        out: Dict[str, Any] = {
            "master_document": fallback_master,
            "structure_outline": fallback_outline,
            "core_arguments": self._fallback_core_arguments(title, core),
            "variants": [],
        }

        if self.llm and self.llm.enabled:
            editorial_brief = self._build_editorial_brief(
                target_audience=target_audience,
                target_audience_notes=target_audience_notes,
                audience_familiarity=audience_familiarity,
                detail_level=detail_level,
                tone_preference=tone_preference,
                stance=stance,
                primary_goal=primary_goal,
                desired_action=desired_action,
                constraints=constraints,
            )

            # ----------------------------
            # Prompts (policy dependent)
            # ----------------------------

            if structure_policy == "structured":
                policy_rules = f"""
STRUCTURE POLICY: STRUCTURED

Hard rules for master_document:
- You MAY include a top-level title line "# {title}" (optional).
- Then use ONLY these H2 headings in this exact order (no extra headings):
  {["## " + h for h in STRUCTURED_HEADINGS]}
- Under "## Key Takeaways": include exactly 5 bullet points (a single bullet list).
- Under "## Core Idea": the first sentence must preserve the core idea meaning.
"""
                outline_instruction = "structure_outline must be the 7 H2 headings in order (without the '## ' prefix)."
            else:
                policy_rules = """
STRUCTURE POLICY: FREEFORM

Rules for master_document:
- Write in a natural, entertaining or informal style if it fits the brief.
- Do NOT force corporate section headings.
- Keep the opening punchy (first 1–2 lines must work as a hook).
- Maintain a clear flow (3–7 beats), and end with a close line (CTA/question).
- You may use short separators or emojis if tone_preference supports it, but avoid overuse.
"""
                outline_instruction = (
                    "structure_outline must be 3–7 short beat labels capturing the flow "
                    '(e.g., ["Hook","Setup","Twist","Punchline","Close"]).'
                )

            base_system_prompt = f"""
You are an expert editorial writer generating CANONICAL master content (platform-agnostic).

Apply this editorial brief STRICTLY:
{editorial_brief}

{policy_rules}

Factuality rules:
- Do NOT invent statistics, named entities, or factual claims not supported by research_context.
  If something is unknown or missing, write "not specified".
- Respect constraints.must_include, constraints.must_avoid, constraints.forbidden_claims.
- Keep tone consistent with tone_preference and the audience brief.

Output rules:
- Return STRICT JSON only. No markdown fences. No commentary. No extra keys.
""".strip()

            base_user_prompt = f"""
Return STRICT JSON with this schema EXACTLY:
{{
  "master_document": "<markdown>",
  "structure_outline": ["<string>", "..."],
  "core_arguments": ["<keyword_or_short_phrase>", "..."]
}}

Inputs:
- title: {title}
- core_idea (preserve meaning): {core}
- user_content: {user_content if user_content else "not specified"}
- research_context (facts source; do not add facts beyond this): {research_context}
- voice_profile_id (placeholder only): {voice_profile_id}

Requirements:
- master_document: follow the structure policy above and the editorial brief.
- {outline_instruction}
- core_arguments: 5-10 short phrases capturing the key arguments, key terms, and implied tags.
""".strip()

            try:
                raw = self.llm.chat(
                    system_prompt=base_system_prompt,
                    user_prompt=base_user_prompt,
                    temperature=0.35 if structure_policy == "structured" else 0.5,
                    max_tokens=2600,
                )
                parsed = parse_json_object(raw)

                if not parsed:
                    logger.warning("MasterContentNode: base LLM output not parseable JSON; using fallback.")
                else:
                    base_document = str(parsed.get("master_document") or fallback_master).strip()

                    # Structured-only: validate/repair so downstream sees stable formatting when expected
                    if structure_policy == "structured" and not self._is_compliant_structured(base_document):
                        base_document = self._repair_structured(
                            bad_doc=base_document,
                            core_idea=core,
                            editorial_brief=editorial_brief,
                            research_context=research_context,
                            title=title,
                        )

                    # Outline handling (policy dependent)
                    structure_outline = parsed.get("structure_outline")
                    if isinstance(structure_outline, list) and structure_outline:
                        base_outline = [str(x).strip() for x in structure_outline if str(x).strip()]
                    else:
                        base_outline = []

                    if structure_policy == "structured":
                        # Enforce stable outline for structured mode
                        base_outline = STRUCTURED_HEADINGS[:]
                    else:
                        # Freeform: if outline empty, derive from headings if present else minimal beats
                        if not base_outline:
                            base_outline = self._derive_outline_freeform(base_document)
                        else:
                            base_outline = base_outline[:10]

                    # Core arguments
                    core_arguments = parsed.get("core_arguments")
                    if not isinstance(core_arguments, list) or not core_arguments:
                        core_arguments = self._fallback_core_arguments(title, core)
                    core_arguments = [str(x).strip() for x in core_arguments if str(x).strip()] or ["not specified"]
                    core_arguments = core_arguments[:12]

                    out = {
                        "master_document": base_document,
                        "structure_outline": base_outline,
                        "core_arguments": core_arguments,
                        "variants": [],
                    }

                    # ----------------------------
                    # Variants (separate calls)
                    # ----------------------------
                    for spec in variants:
                        eff_user, eff_research = self._effective_weights(user_content, spec.weight_user, spec.weight_research)
                        variant_directive = self._variant_directive(spec, stance, primary_goal, desired_action)

                        user_anchor = (
                            f"Anchor ~{int(eff_user*100)}% of the framing to user_content (intent, phrasing, examples)."
                            if eff_user > 0 else
                            "User_content is not specified; do not cite it as a source."
                        )
                        research_anchor = f"Anchor ~{int(eff_research*100)}% of grounded points to research_context."

                        # Temperature tuning: a bit freer for entertain + narrative
                        temp = 0.6 if (primary_goal == "entertain" and spec.structure == "narrative_first") else (0.4 if structure_policy == "freeform" else 0.35)

                        # Policy-specific variant rules
                        if structure_policy == "structured":
                            variant_policy_rules = f"""
Variant must follow STRUCTURED policy:
- Optional "# {title}" title line.
- Then ONLY these H2 headings in this exact order:
  {["## " + h for h in STRUCTURED_HEADINGS]}
- Exactly 5 bullets under "## Key Takeaways".
- First sentence under "## Core Idea" preserves meaning of: {core}
"""
                            variant_outline_instruction = "structure_outline must be the 7 H2 headings in order (without the '## ' prefix)."
                        else:
                            variant_policy_rules = """
Variant must follow FREEFORM policy:
- Natural style aligned to brief; no forced corporate headings.
- Opening is a strong hook (first 1–2 lines).
- Maintain 3–7 beats; end with a close line (CTA/question).
"""
                            variant_outline_instruction = (
                                "structure_outline must be 3–7 short beat labels capturing the flow "
                                '(e.g., ["Hook","Setup","Twist","Punchline","Close"]).'
                            )

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
  "structure_outline": ["<string>", "..."]
}}

Variant spec:
- label: {spec.label}
- levers: weight_user={eff_user}, weight_research={eff_research}, structure={spec.structure}
- directive: {variant_directive}
- anchoring: {user_anchor} {research_anchor}

Inputs:
- title: {title}
- core_idea (preserve meaning): {core}
- user_content: {user_content if user_content else "not specified"}
- research_context (facts source; do not add facts beyond this): {research_context}
- voice_profile_id (placeholder only): {voice_profile_id}

Rules:
{variant_policy_rules}

Also:
- {variant_outline_instruction}
- Keep output grounded: do NOT invent facts beyond research_context. Unknown -> "not specified".
""".strip()

                        try:
                            v_raw = self.llm.chat(
                                system_prompt=base_system_prompt,
                                user_prompt=variant_user_prompt,
                                temperature=temp,
                                max_tokens=2200,
                            )
                            v_parsed = parse_json_object(v_raw)
                            if not v_parsed:
                                logger.warning("MasterContentNode: variant output not parseable JSON; skipping.")
                                continue

                            v_doc = str(v_parsed.get("master_document") or "").strip()
                            if not v_doc:
                                continue

                            # Structured-only: validate/repair
                            if structure_policy == "structured" and not self._is_compliant_structured(v_doc):
                                v_doc = self._repair_structured(
                                    bad_doc=v_doc,
                                    core_idea=core,
                                    editorial_brief=editorial_brief,
                                    research_context=research_context,
                                    title=title,
                                )

                            # Outline extraction / fallback
                            v_outline_raw = v_parsed.get("structure_outline")
                            if isinstance(v_outline_raw, list) and v_outline_raw:
                                v_outline = [str(x).strip() for x in v_outline_raw if str(x).strip()]
                            else:
                                v_outline = []

                            if structure_policy == "structured":
                                v_outline = STRUCTURED_HEADINGS[:]
                            else:
                                if not v_outline:
                                    v_outline = self._derive_outline_freeform(v_doc)
                                else:
                                    v_outline = v_outline[:10]

                            out["variants"].append(
                                {
                                    "id": spec.id,
                                    "label": spec.label,  # canonical label
                                    "levers": {
                                        "weight_user": float((v_parsed.get("levers") or {}).get("weight_user") or eff_user),
                                        "weight_research": float((v_parsed.get("levers") or {}).get("weight_research") or eff_research),
                                        "structure": str((v_parsed.get("levers") or {}).get("structure") or spec.structure),
                                    },
                                    "master_document": v_doc,
                                    "structure_outline": v_outline,
                                }
                            )
                        except Exception:
                            logger.exception("MasterContentNode: variant generation failed; skipping.")
                            continue

            except Exception:
                logger.exception("MasterContentNode: base generation failed; using fallback.")

        # ----------------------------
        # Output contract (UNCHANGED)
        # ----------------------------
        contract_out = {
            "master_document": str(out.get("master_document") or fallback_master).strip(),
            "structure_outline": [str(x) for x in (out.get("structure_outline") or fallback_outline)],
            "core_arguments": [str(x) for x in (out.get("core_arguments") or ["not specified"])],
            "master_variants": [],
        }

        # Normalize base outline a bit
        if not contract_out["structure_outline"]:
            contract_out["structure_outline"] = fallback_outline

        # Add variants (same contract fields as before)
        for variant in out.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            label = str(variant.get("label") or "").strip()
            document = str(variant.get("master_document") or "").strip()
            if not label or not document:
                continue

            variant_outline = variant.get("structure_outline")
            if isinstance(variant_outline, list) and variant_outline:
                normalized_outline = [str(x) for x in variant_outline if str(x).strip()]
            else:
                normalized_outline = (
                    STRUCTURED_HEADINGS[:] if structure_policy == "structured"
                    else self._derive_outline_freeform(document)
                )

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
        
