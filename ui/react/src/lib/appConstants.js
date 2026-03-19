export const API_BASE_DEFAULT =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8010";

export const TOPIC_TITLE_SUGGESTION = "A practical lesson from shipping a product with a small team";
export const CORE_IDEA_SUGGESTION = "Small teams move faster when they reduce scope early and iterate in public.";
export const USER_CONTENT_SUGGESTION = `Add any raw notes, examples, links, rough draft paragraphs, or source material here.

Helpful inputs:
- a short summary of the topic
- the audience you want to reach
- any claims, examples, or numbers to include
- brand voice notes or writing constraints
- a draft you want improved or repurposed`;

export const AUDIENCE_OPTIONS = [
  { value: "general", label: "General" },
  { value: "professionals", label: "Professionals (white-collar)" },
  { value: "creators_influencers", label: "Creators / Influencers" },
  { value: "small_business_owners", label: "Small business owners" },
  { value: "founders_entrepreneurs", label: "Founders / Entrepreneurs" },
  { value: "builders_developers", label: "Builders / Developers" },
  { value: "marketing_growth", label: "Marketing / Growth" },
  { value: "sales_partnerships", label: "Sales / Partnerships" },
  { value: "enterprise_leaders", label: "Enterprise leaders" },
  { value: "other", label: "Other" },
];

export const AUDIENCE_FAMILIARITY_OPTIONS = [
  { value: "new", label: "New" },
  { value: "somewhat_familiar", label: "Somewhat familiar" },
  { value: "very_familiar", label: "Very familiar" },
];

export const DETAIL_LEVEL_OPTIONS = [
  { value: "quick_take", label: "Quick take" },
  { value: "practical", label: "Practical" },
  { value: "deep_dive", label: "Deep dive" },
];

export const TONE_OPTIONS = ["professional", "analytical", "conversational"];
export const STANCE_OPTIONS = ["supportive", "contrarian", "balanced"];
export const PRIMARY_GOAL_OPTIONS = ["educate", "thought_leadership", "promote", "entertain", "recruit", "community", "convert"];
export const DESIRED_ACTION_OPTIONS = ["comment", "share", "follow", "click", "dm", "subscribe", "buy"];

export const ARTIFACT_FORMAT_DISPLAY_ORDER = {
  text: [
    "caption",
    "post",
    "blog",
    "newsletter",
    "script_short",
    "cta_variants",
  ],
  image: ["post_image", "thumbnail", "banner", "cover"],
};

export const ARTIFACT_FORMAT_DESCRIPTIONS = {
  caption: "short, punchy, skimmable",
  post: "short-form post, platform-neutral",
  newsletter: "email edition",
  blog: "long-form",
  script_short: "short voiceover",
  cta_variants: "multiple CTAs",
  post_image: "square/portrait social image",
  thumbnail: "thumbnail visual",
  banner: "wide banner visual",
  cover: "cover image",
  video: "video concept / plan",
};

export const ARTIFACT_FORMAT_TITLES = {
  caption: "Caption",
  post: "Post",
  blog: "Blog",
  newsletter: "Newsletter",
  script_short: "Short Script",
  cta_variants: "CTA",
  post_image: "Post Image",
  thumbnail: "Thumbnail",
  banner: "Banner",
  cover: "Cover Image",
  gif: "Gif",
  reel: "Reel",
  short_video: "Short Video",
};

export const ARTIFACT_TONE_BASE_DEFAULTS = {
  analytical: {
    directness: 3,
    warmth: 1,
    energy: 2,
    authority: 3,
    rigor: 4,
    abstraction: 2,
    framework_mode: "light",
  },
  professional: {
    directness: 3,
    warmth: 2,
    energy: 2,
    authority: 3,
    formality: 3,
    diplomacy: 3,
  },
  conversational: {
    directness: 2,
    warmth: 3,
    energy: 3,
    authority: 2,
    humor: "light",
    storyness: 3,
  },
};

export const FORMAT_ADVANCED_DEFAULTS = {
  caption: { length: "short", emoji_density: "light", structure_hint: "plain" },
  post: { length: "medium", structure_hint: "framework-led", cta_strength: "medium" },
  newsletter: { sections: 4, takeaway_bullets: 4, cta_strength: "medium" },
  blog: { seo_intent: "informational", faq_count: 3, cta_strength: "medium" },
  script_short: { target_duration_sec: 30, pacing: "normal", cta_strength: "medium" },
  cta_variants: { variant_count: 7, angles: ["benefit", "question"] },
};
