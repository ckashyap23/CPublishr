# DOCUMENT 2 — MVP Sequencing (Phased Build Plan + Scope Control)

## Guiding principle

Don’t scale mediocre ideas into many formats.
**Win text + voice + platform fit first**, then add publishing/analytics, then experiments, then multimodal.

---

## Phase 0 — Foundation (must-have plumbing)

**Goal:** make the system stable and learnable.

Deliverables:

* Project-wide content schema (Brief → Research → Master → Artifacts)
* Prompt + tool abstraction layer (so you can swap models/tools)
* Versioning: every output stored with lineage (inputs, prompts, sources, edits)
* Basic safety: PII redaction, similarity guardrails (light)

Exit criteria:

* You can reproduce outputs with consistent configs
* You can track which artifact came from which master + research

---

## Phase 1 — Text MVP That Doesn’t Sound Fake (Highest priority)

**Goal:** generate strong platform-native text with user voice consistency.

In scope:

1. **Brief Builder v1**

   * topic, thesis, audience, platform, objective, tone
2. **Research Agent v1**

   * curated bullet insights + optional evidence list
3. **Master Content Studio v1**

   * 3–5 angles (framework/story/contrarian/how-to/promo)
   * editing controls: shorten/expand/clarify/more-bold/more-me
4. **Platform Adapters v1** (start with 2 platforms)

   * LinkedIn + X (most feedback, fastest iteration)
5. **Voice Profile v1**

   * onboarding via 3–10 past posts or sample writing
   * “do/don’t” rules + tone sliders
6. **Artifact outputs v1 (text)**

   * LinkedIn: short + long version
   * X: single tweet + thread (6–10 tweets)
   * Hashtag/tag suggestions (rule-based + pattern library)

Out of scope (explicitly cut for now):

* Scheduling integrations
* Exact engagement prediction
* Images/videos generation

Exit criteria:

* Users accept a generated draft with light edits
* Users say: “this sounds like me” (qualitative + simple rating)
* Platform formatting is correct and export-ready

---

## Phase 2 — Repurposing & Campaign Mode (Stickiness Upgrade)

**Goal:** turn one idea into a week’s worth of coherent output.

In scope:

1. **Repurposing engine**

   * master → blog outline + newsletter draft
   * master → Insta carousel script (text-only)
   * master → reel script + beat sheet (text-only)
2. **Campaign mode**

   * user selects a pillar → generates 5–10 post ideas
   * creates a cohesive series (Part 1/2/3…) with consistent arc
3. **Reusable templates**

   * thought-leadership, educational, promo, storytelling, hiring, case study

Exit criteria:

* One brief reliably yields a multi-platform pack
* Users return because it saves planning time, not just writing time

---

## Phase 3 — Publishing Workflow + Analytics Ingestion (Close the loop)

**Goal:** start learning from real outcomes.

In scope:

1. **Export & scheduling-lite**

   * clean copy packs for each platform
   * optional reminders / calendar integration later
2. **Metrics ingestion v1**

   * manual entry allowed initially (fast + low integration burden)
   * later: platform APIs where feasible
3. **Post metadata tracking**

   * hook type, format type, length, CTA type, tags
4. **Insights dashboard v1**

   * “what worked” in plain English
   * recommendations: best hook types, best lengths, best topics

Exit criteria:

* You can tie a generated artifact to performance metrics
* System can recommend improvements based on *user’s own history*

---

## Phase 4 — Variant Testing (A/B) + Explainable Scorecards

**Goal:** systematic improvement, not guesswork.

In scope:

1. **Variant generator**

   * 3 versions with controlled differences (hook / CTA / structure)
2. **Scorecards**

   * hook strength, clarity, novelty, platform fit, CTA strength, risk flags
   * explanations (“why version B is stronger than A”)
3. **A/B testing workflow**

   * comparable posting slot guidance
   * treatment vs control comparison

Exit criteria:

* Users can run simple experiments and see measurable deltas
* Your recommendations improve over time per user

---

## Phase 5 — Multimodal Artifacts (Images/Video/Audio) Built on a Strong “Brain”

**Goal:** expand formats without sacrificing quality.

In scope (recommended order):

1. **Carousel visuals pipeline**

   * slide headlines + body copy + design tokens (brand kit)
   * image prompts for each slide (optional)
2. **Thumbnail/poster prompts**
3. **Short video pipeline**

   * beat sheet + shot list + caption timing + b-roll suggestions
4. **Audio**

   * voiceover scripts + pacing marks

Exit criteria:

* Multimodal outputs stay consistent with master narrative + user voice
* Users can publish with minimal manual assembly

---

## Cross-cutting: Top 15 MVP User Stories (you can turn into backlog)

1. As a user, I can input a brief (topic/thesis/audience/platform/goal).
2. I can paste past posts to create a voice profile.
3. I can generate 3–5 master angles and choose one.
4. I can edit with “shorter / clearer / more bold / more me”.
5. I can generate LinkedIn post (short + long).
6. I can generate X tweet + thread from the same master.
7. I can get tags/hashtags aligned to my niche and platform norms.
8. I can export formatted copy ready to paste.
9. I can save masters and reuse them later.
10. I can generate a “series plan” from one topic (campaign mode).
11. I can repurpose into blog/newsletter outline.
12. I can store a brand kit (bio, positioning, do/don’t).
13. I can view a quality scorecard explaining strengths/risks.
14. I can store published links + metrics manually.
15. I can generate 3 variants and compare performance.

---

## Scope Control: What NOT to do too early (common traps)

* “Training on scraped viral posts” (use pattern RAG + features instead)
* Hard “engagement prediction number” (do relative scoring + A/B)
* Multimodal generation before voice + platform-fit text is excellent
* Too many platforms at once (start with 2, then expand)

---

## Suggested Initial Platform Focus

**Start:** LinkedIn + X
**Next:** Medium/newsletter (long-form repurpose)
**Then:** Insta carousels + Reels/Shorts scripts (text-first)
**Finally:** full multimodal generation + scheduling + advanced experimentation

---
