import React, { useEffect, useMemo, useRef, useState } from "react";
import publishrLogo from "./publishr_logo.png";

const API_BASE_DEFAULT = "http://127.0.0.1:8010";

const TOPIC_TITLE_SUGGESTION = "Cats are better than dogs";
const CORE_IDEA_SUGGESTION = "Cats are better than dogs";
const USER_CONTENT_SUGGESTION = `When it comes to choosing a pet, the age-old debate of cats versus dogs often takes center stage. But what if we told you that cats might just be the superior choice? Let's explore why these independent furballs could rule the world of pets.

## The Unique Qualities of Cats
Cats are the only pets that come with built-in self-cleaning, boundary setting, and 'I chose you' energy. Unlike dogs, who love everyone like a free trial, cats love you like a premium subscription-earned, exclusive, and occasionally renewed with snacks. Their independence means they can thrive on their own, making them perfect for busy lifestyles.

## Lower Maintenance Needs
One of the standout features of cats is their lower maintenance requirements. They don't need daily walks or constant attention, which can be a game changer for pet owners with a hectic schedule. This independence allows you to enjoy their company without the added stress of high maintenance.

## Why Cats Could Rule the World
Imagine a world where cats reign supreme. With their unique qualities and independent nature, they not only make great companions but also have the potential to be the ultimate pet. Here are a few reasons why:
- Built-in self-cleaning habits
- Less demanding than dogs
- Independent and self-sufficient
- Exclusive affection that feels earned
- Perfect for busy lifestyles

In the end, while both cats and dogs have their merits, it's hard to ignore the remarkable qualities that cats bring to the table. They might just be the perfect pet to rule the world, one purr at a time.`;

const AUDIENCE_OPTIONS = [
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
const AUDIENCE_FAMILIARITY_OPTIONS = [
  { value: "new", label: "New" },
  { value: "somewhat_familiar", label: "Somewhat familiar" },
  { value: "very_familiar", label: "Very familiar" },
];
const DETAIL_LEVEL_OPTIONS = [
  { value: "quick_take", label: "Quick take" },
  { value: "practical", label: "Practical" },
  { value: "deep_dive", label: "Deep dive" },
];
const TONE_OPTIONS = ["professional", "analytical", "conversational"];
const STANCE_OPTIONS = ["supportive", "contrarian", "balanced"];
const PRIMARY_GOAL_OPTIONS = ["educate", "thought_leadership", "promote", "entertain", "recruit", "community", "convert"];
const DESIRED_ACTION_OPTIONS = ["comment", "share", "follow", "click", "dm", "subscribe", "buy"];
const ARTIFACT_FORMAT_DISPLAY_ORDER = {
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

const ARTIFACT_FORMAT_DESCRIPTIONS = {
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

const ARTIFACT_TONE_BASE_DEFAULTS = {
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

const FORMAT_ADVANCED_DEFAULTS = {
  caption: { length: "short", emoji_density: "light", structure_hint: "plain" },
  post: { length: "medium", structure_hint: "framework-led", cta_strength: "medium" },
  newsletter: { sections: 4, takeaway_bullets: 4, cta_strength: "medium" },
  blog: { seo_intent: "informational", faq_count: 3, cta_strength: "medium" },
  script_short: { target_duration_sec: 30, pacing: "normal", cta_strength: "medium" },
  cta_variants: { variant_count: 7, angles: ["benefit", "question"] },
};

function makeDefaultFormatAdvancedSettings() {
  return {
    caption: { ...FORMAT_ADVANCED_DEFAULTS.caption },
    post: { ...FORMAT_ADVANCED_DEFAULTS.post },
    newsletter: { ...FORMAT_ADVANCED_DEFAULTS.newsletter },
    blog: { ...FORMAT_ADVANCED_DEFAULTS.blog },
    script_short: { ...FORMAT_ADVANCED_DEFAULTS.script_short },
    cta_variants: { ...FORMAT_ADVANCED_DEFAULTS.cta_variants, angles: [...FORMAT_ADVANCED_DEFAULTS.cta_variants.angles] },
  };
}

function makeDefaultImageStyleSettings() {
  return {
    theme: "",
    subject_prompt: "",
    avoid: ["watermark", "gibberish text"],
    medium: "illustration",
    texture: "clean",
    lighting: "soft_daylight",
    palette_mode: "muted",
    brand_colors: {
      primary: "#0F172A",
      secondary: "#1D4ED8",
      accent: "#22C55E",
      background: "#F8FAFC",
    },
    mood: "premium",
    focus_negative_space: "subject_centered",
    output_fidelity: "standard",
  };
}

function toneBaseFromProjectTone(tonePreference) {
  const t = String(tonePreference || "").trim().toLowerCase();
  if (t === "analytical") return "analytical";
  if (t === "professional") return "professional";
  return "conversational";
}

function makeDefaultToneNuance(toneBase) {
  const base = ARTIFACT_TONE_BASE_DEFAULTS[toneBase] || ARTIFACT_TONE_BASE_DEFAULTS.conversational;
  return { tone_base: toneBase, ...base };
}

function clampInt(value, min, max, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, Math.round(n)));
}

function humorLabelToSlider(value) {
  const v = String(value || "").trim().toLowerCase();
  if (v === "none") return 0;
  if (v === "playful") return 2;
  return 1; // light default
}

function humorSliderToLabel(value) {
  const n = Number(value);
  if (n <= 0) return "none";
  if (n >= 2) return "playful";
  return "light";
}

function normalizeVoiceProfilePreview(detail) {
  if (!detail || typeof detail !== "object") return null;
  return {
    core_voice: String(detail?.version?.core_voice || detail?.raw_profile_json?.core_voice || "").trim(),
    tone_baseline: detail?.tone_baseline && typeof detail.tone_baseline === "object" ? detail.tone_baseline : {},
    style_summary: detail?.style_summary && typeof detail.style_summary === "object" ? detail.style_summary : {},
    do_rules: Array.isArray(detail?.do_rules) ? detail.do_rules.map((x) => String(x || "").trim()).filter(Boolean) : [],
    dont_rules: Array.isArray(detail?.dont_rules) ? detail.dont_rules.map((x) => String(x || "").trim()).filter(Boolean) : [],
    exemplars: Array.isArray(detail?.raw_profile_json?.exemplars) ? detail.raw_profile_json.exemplars.slice(0, 4) : [],
  };
}

function artifactFormatMeta(fmt) {
  const key = String(fmt || "").trim();
  return {
    key,
    title: key,
    description: ARTIFACT_FORMAT_DESCRIPTIONS[key] || "",
  };
}

function makeDefaultVideoStyleSettings() {
  return {
    theme: "",
    subject_prompt: "",
    avoid: ["watermarks", "logos", "ui screenshots", "real people"],
    mood: "energetic",
    lighting: "soft_daylight",
    palette_mode: "muted",
    brand_colors: {
      primary: "#0F172A",
      secondary: "#1D4ED8",
      accent: "#22C55E",
      background: "#F8FAFC",
    },
    output_fidelity: "standard",
    camera_motion: "",
    energy_level: "medium",
  };
}

function defaultPublishPartForArtifact(artifact) {
  if (!artifact || typeof artifact !== "object") return "";
  const fmt = String(artifact?.format || "").trim();
  const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
  if (["caption", "post", "newsletter", "blog"].includes(fmt)) return "body";
  if (["cta_variants", "script_short"].includes(fmt)) return "items";
  if (["post_image", "thumbnail", "banner", "cover"].includes(fmt)) return "assets";
  if (typeof payload.body === "string" && payload.body.trim()) return "body";
  if (Array.isArray(payload.items) && payload.items.length) return "items";
  if (Array.isArray(payload.assets) && payload.assets.length) return "assets";
  if (String(artifact?.title || "").trim()) return "title";
  return "";
}

function artifactHasTags(artifact) {
  return Array.isArray(artifact?.tags_json) && artifact.tags_json.some((t) => String(t || "").trim());
}

function extractImageStyleSeedFromArtifact(artifact) {
  if (!artifact || typeof artifact !== "object") return null;
  const fmt = String(artifact?.format || "").trim();
  if (!["post_image", "thumbnail", "banner", "cover", "image_generation"].includes(fmt)) return null;
  const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
  const settings = payload?.settings && typeof payload.settings === "object" ? payload.settings : {};
  const imageStyle = settings?.image_style && typeof settings.image_style === "object" ? settings.image_style : {};
  const theme = String(imageStyle?.theme || "").trim();
  const subjectPrompt = String(imageStyle?.subject_prompt || "").trim();
  const paletteMode = String(imageStyle?.palette_mode || "").trim();
  const mood = String(imageStyle?.mood || "").trim();
  if (!theme && !subjectPrompt && !paletteMode && !mood) return null;
  return { theme, subject_prompt: subjectPrompt, palette_mode: paletteMode, mood };
}

function pickLatestImageStyleSeed(artifacts) {
  const items = Array.isArray(artifacts) ? artifacts : [];
  let best = null;
  let bestTs = -1;
  for (const a of items) {
    const seed = extractImageStyleSeedFromArtifact(a);
    if (!seed) continue;
    const ts = Date.parse(a?.updated_at || a?.created_at || "") || 0;
    if (ts >= bestTs) {
      bestTs = ts;
      best = seed;
    }
  }
  return best;
}

function makePublishSourceRow() {
  return {
    source_id: `src_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    artifact_id: "",
    primary_part: "",
    include_tags: false,
    render_as: "",
    order: null,
  };
}

function orderArtifactFormats(kind, formats) {
  const items = Array.isArray(formats) ? [...formats] : [];
  const preferred = ARTIFACT_FORMAT_DISPLAY_ORDER[kind] || [];
  if (!preferred.length) return items;
  const rank = new Map(preferred.map((fmt, idx) => [fmt, idx]));
  return items.sort((a, b) => {
    const aRank = rank.has(a) ? rank.get(a) : Number.MAX_SAFE_INTEGER;
    const bRank = rank.has(b) ? rank.get(b) : Number.MAX_SAFE_INTEGER;
    if (aRank !== bRank) return aRank - bRank;
    return String(a).localeCompare(String(b));
  });
}

function LabelWithTooltip({ text, tooltip, required = false }) {
  return (
    <div className="label-row">
      <label>
        {text}
        {required ? <span className="publish-required-mark"> *</span> : null}
      </label>
      {tooltip ? (
        <span className="tooltip-icon" title={tooltip} aria-label={tooltip} tabIndex={0} role="note">
          ?
        </span>
      ) : null}
    </div>
  );
}
async function apiRequest(baseUrl, method, path, body, token = "") {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const txt = await res.text();
  let json = null;
  try {
    json = txt ? JSON.parse(txt) : null;
  } catch {
    json = null;
  }
  if (!res.ok) {
    const detail = json?.detail ? JSON.stringify(json.detail) : txt || `HTTP ${res.status}`;
    throw new Error(`${res.status} ${detail}`);
  }
  return json;
}

function encodePathSegment(value) {
  return encodeURIComponent(String(value || "").trim());
}

function getVersionLabel(v) {
  if (v.version_kind === "base") return "base";
  if (v.version_kind === "variant") return v.variant_label || `variant v${v.version_number}`;
  if (v.version_kind === "editorial") return v.variant_label || `editorial v${v.version_number}`;
  return `version ${v.version_number}`;
}

function uniqueStrings(values) {
  const out = [];
  const seen = new Set();
  for (const v of Array.isArray(values) ? values : []) {
    const s = String(v || "").trim();
    if (!s) continue;
    const key = s.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(s);
  }
  return out;
}

function hashtagListFromArtifact(artifact) {
  const tags = uniqueStrings(artifact?.tags_json);
  const fromTags = tags.filter((t) => t.startsWith("#"));
  if (fromTags.length) return fromTags;
  const body = String(artifact?.payload_json?.body || "");
  const matches = body.match(/#[\p{L}\p{N}_]+/gu) || [];
  return uniqueStrings(matches);
}

function topicTagListFromArtifact(artifact) {
  return uniqueStrings(artifact?.tags_json).filter((t) => !t.startsWith("#"));
}

function imageSrcFromAsset(asset) {
  const uri = String(asset?.uri || "");
  if (/^(data:|https?:|blob:)/i.test(uri)) return uri;
  if (/^file:\/\//i.test(uri)) return uri;
  const path = String(asset?.path || "");
  if (/^[A-Za-z]:\\/.test(path)) {
    return `file:///${path.replace(/\\/g, "/")}`;
  }
  return "";
}

function videoSrcFromAsset(asset) {
  const uri = String(asset?.uri || "");
  if (/^(data:|https?:|blob:)/i.test(uri)) return uri;
  if (/^file:\/\//i.test(uri)) return uri;
  const path = String(asset?.path || "");
  if (/^[A-Za-z]:\\/.test(path)) {
    return `file:///${path.replace(/\\/g, "/")}`;
  }
  return "";
}

function autoResizeTextarea(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}

export default function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(API_BASE_DEFAULT);
  const [authToken, setAuthToken] = useState(() => window.localStorage.getItem("cpublishr_token") || "");
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ user_id: "", email: "", password: "" });
  const [currentUser, setCurrentUser] = useState(null);
  const [page, setPage] = useState("setup");
  const [busy, setBusy] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [nodeAudit, setNodeAudit] = useState([]);
  const [canContinueToEditorial, setCanContinueToEditorial] = useState(false);
  const [hasExistingContent, setHasExistingContent] = useState(false);
  const [isCheckingProjectData, setIsCheckingProjectData] = useState(false);
  const [showGenerateSetupForm, setShowGenerateSetupForm] = useState(true);

  const [form, setForm] = useState({
    project_id: "proj_local_1",
    topic_title: "",
    core_idea: "",
    user_content: "",
    target_audience_segment: "general",
    target_audience_notes: "",
    audience_familiarity: "somewhat_familiar",
    detail_level: "quick_take",
    tone_preference: "conversational",
    stance: "balanced",
    primary_goal: "community",
    desired_action: "comment",
    voice_profile_id: "",
    distribution_targets: ["x", "instagram"],
  });

  const [versions, setVersions] = useState([]);
  const [selectedVersionNumber, setSelectedVersionNumber] = useState(null);
  const [keywordsInput, setKeywordsInput] = useState("");
  const [workingContent, setWorkingContent] = useState("");
  const [feedbackText, setFeedbackText] = useState("Improve clarity and tighten repetitive sections.");
  const [feedbackPreviewContent, setFeedbackPreviewContent] = useState("");
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [editorMode, setEditorMode] = useState("none"); // none | inline | iterate
  const [selectedArtifactFormats, setSelectedArtifactFormats] = useState([]);
  const [artifactFormatsByKind, setArtifactFormatsByKind] = useState({});
  const [artifactOutput, setArtifactOutput] = useState(null);
  const [selectedArtifactTab, setSelectedArtifactTab] = useState(0);
  const [storedArtifacts, setStoredArtifacts] = useState([]);
  const [selectedStoredFormat, setSelectedStoredFormat] = useState("");
  const [selectedStoredArtifactTab, setSelectedStoredArtifactTab] = useState(0);
  const [isArtifactGenerating, setIsArtifactGenerating] = useState(false);
  const [isStoredArtifactsLoading, setIsStoredArtifactsLoading] = useState(false);
  const [hasStoredArtifactsForProject, setHasStoredArtifactsForProject] = useState(false);
  const [isCheckingStoredArtifacts, setIsCheckingStoredArtifacts] = useState(false);
  const [storedArtifactFormatsForProject, setStoredArtifactFormatsForProject] = useState([]);
  const [artifactsViewMode, setArtifactsViewMode] = useState("");
  const [artifactGenerateStep, setArtifactGenerateStep] = useState("formats");
  const [artifactStyleSource, setArtifactStyleSource] = useState("manual");
  const [artifactStyleVoiceProfileId, setArtifactStyleVoiceProfileId] = useState("");
  const [artifactStyleVoiceProfileDetail, setArtifactStyleVoiceProfileDetail] = useState(null);
  const [isArtifactStyleVoiceProfileLoading, setIsArtifactStyleVoiceProfileLoading] = useState(false);
  const [artifactManualCoreVoice, setArtifactManualCoreVoice] = useState("");
  const [artifactToneNuance, setArtifactToneNuance] = useState(() => makeDefaultToneNuance("conversational"));
  const [artifactFrameworkMode, setArtifactFrameworkMode] = useState("light");
  const [artifactFormatAdvanced, setArtifactFormatAdvanced] = useState(() => makeDefaultFormatAdvancedSettings());
  const [artifactAdvancedOpen, setArtifactAdvancedOpen] = useState({});
  const [artifactImageStyle, setArtifactImageStyle] = useState(() => makeDefaultImageStyleSettings());
  const [artifactImageAvoidInput, setArtifactImageAvoidInput] = useState("");
  const [artifactVideoStyle, setArtifactVideoStyle] = useState(() => makeDefaultVideoStyleSettings());
  const [artifactVideoAvoidInput, setArtifactVideoAvoidInput] = useState("");
  const [artifactStyleKindPanel, setArtifactStyleKindPanel] = useState("text");
  const [publishPlatforms, setPublishPlatforms] = useState([]);
  const [isPublishPlatformsLoading, setIsPublishPlatformsLoading] = useState(false);
  const [publishSelectedPlatform, setPublishSelectedPlatform] = useState("");
  const [publishFieldSchema, setPublishFieldSchema] = useState([]);
  const [isPublishFieldSchemaLoading, setIsPublishFieldSchemaLoading] = useState(false);
  const [publishArtifacts, setPublishArtifacts] = useState([]);
  const [isPublishArtifactsLoading, setIsPublishArtifactsLoading] = useState(false);
  const [publishFieldMappings, setPublishFieldMappings] = useState({});
  const [publishSaveMessage, setPublishSaveMessage] = useState("");
  const [showPublishSaveDialog, setShowPublishSaveDialog] = useState(false);
  const [publishSaveUserName, setPublishSaveUserName] = useState("");
  const [publishSaveDestinationMode, setPublishSaveDestinationMode] = useState(() => {
    const raw = window.localStorage.getItem("cpublishr_publish_destination_mode") || "url";
    return raw === "local" ? "local" : "url";
  }); // url | local
  const [publishSaveOutputPath, setPublishSaveOutputPath] = useState(
    () => window.localStorage.getItem("cpublishr_publish_output_path") || ""
  );
  const [publishBrowseCurrentPath, setPublishBrowseCurrentPath] = useState("");
  const [publishBrowseParentPath, setPublishBrowseParentPath] = useState("");
  const [publishBrowseDirectories, setPublishBrowseDirectories] = useState([]);
  const [isPublishBrowsingPaths, setIsPublishBrowsingPaths] = useState(false);
  const [isPublishPickingLocalPath, setIsPublishPickingLocalPath] = useState(false);
  const [artifactEditMode, setArtifactEditMode] = useState("none"); // none | inline | iterate
  const [isArtifactEditing, setIsArtifactEditing] = useState(false);
  const [artifactInlineText, setArtifactInlineText] = useState("");
  const [artifactIterateInstruction, setArtifactIterateInstruction] = useState("");
  const [artifactIterateStyleSource, setArtifactIterateStyleSource] = useState("manual");
  const [artifactIterateVoiceProfileId, setArtifactIterateVoiceProfileId] = useState("");
  const [artifactIterateManualCoreVoice, setArtifactIterateManualCoreVoice] = useState("");
  const [artifactIterateToneNuance, setArtifactIterateToneNuance] = useState(() => makeDefaultToneNuance("conversational"));
  const [artifactIterateFrameworkMode, setArtifactIterateFrameworkMode] = useState("light");
  const [artifactIterateFormatAdvanced, setArtifactIterateFormatAdvanced] = useState(() => makeDefaultFormatAdvancedSettings());
  const [artifactIterateImageStyle, setArtifactIterateImageStyle] = useState(() => ({
    medium: "illustration",
    texture: "clean",
    lighting: "soft_daylight",
    palette_mode: "muted",
    mood: "premium",
    focus_negative_space: "subject_centered",
    output_fidelity: "standard",
    brand_colors: {
      primary: "#0F172A",
      secondary: "#1D4ED8",
      accent: "#22C55E",
      background: "#F8FAFC",
    },
  }));
  const [artifactIterateVideoStyle, setArtifactIterateVideoStyle] = useState(() => ({
    mood: "energetic",
    lighting: "soft_daylight",
    palette_mode: "muted",
    output_fidelity: "standard",
    camera_motion: "",
    energy_level: "medium",
    brand_colors: {
      primary: "#0F172A",
      secondary: "#1D4ED8",
      accent: "#22C55E",
      background: "#F8FAFC",
    },
  }));
  const [editingArtifactTitleId, setEditingArtifactTitleId] = useState("");
  const [editingArtifactTitleValue, setEditingArtifactTitleValue] = useState("");
  const [isSavingArtifactTitle, setIsSavingArtifactTitle] = useState(false);

  const [vpCollections, setVpCollections] = useState([]);
  const [vpSelectedCollectionId, setVpSelectedCollectionId] = useState("");
  const [vpCollectionDetail, setVpCollectionDetail] = useState(null);
  const [vpSelectedVersionId, setVpSelectedVersionId] = useState("");
  const [vpVersionDetail, setVpVersionDetail] = useState(null);
  const [showVpVersionControls, setShowVpVersionControls] = useState(false);
  const [showVpCreateCollectionForm, setShowVpCreateCollectionForm] = useState(false);
  const [vpCreateForm, setVpCreateForm] = useState({ voice_profile_name: "", platforms: ["linkedin"] });
  const [vpGenerateForm, setVpGenerateForm] = useState({
    intended_use: "",
    datasets: [{ dataset_name: "", source_profile: "", blob_prefix: "", sample_scope_note: "" }],
  });
  const [vpStatusInput, setVpStatusInput] = useState("approved");
  const [isVpGenerating, setIsVpGenerating] = useState(false);
  const [userProjects, setUserProjects] = useState([]);
  const [isProjectsLoading, setIsProjectsLoading] = useState(false);
  const [hasManuallyEditedProjectId, setHasManuallyEditedProjectId] = useState(false);
  const [isCreatingNewProject, setIsCreatingNewProject] = useState(false);
  const contentCheckSeqRef = useRef(0);
  const storedArtifactsCheckSeqRef = useRef(0);
  const artifactStyleSeedFetchRef = useRef("");
  const artifactInlineTextareaRef = useRef(null);
  const artifactIterateInstructionTextareaRef = useRef(null);
  const artifactIterateVoiceStyleTextareaRef = useRef(null);
  const editorialInlineTextareaRef = useRef(null);
  const editorialFeedbackTextareaRef = useRef(null);
  const userContentTextareaRef = useRef(null);
  const isAuthenticated = !!authToken;
  const currentProjectSummary = useMemo(() => {
    const current = String(form.project_id || "").trim();
    if (!current) return null;
    return userProjects.find((p) => String(p?.project_id || "").trim() === current) || null;
  }, [userProjects, form.project_id]);
  const isExistingProjectFlow = isAuthenticated && !!currentProjectSummary && !isCreatingNewProject;
  const finalizedVersionBanner = useMemo(() => {
    const finalVersionNumber = Number(currentProjectSummary?.final_version_number);
    const list = Array.isArray(versions) ? versions : [];
    const fromProject = Number.isFinite(finalVersionNumber)
      ? list.find((v) => Number(v?.version_number) === finalVersionNumber) || null
      : null;
    const fallbackFinal = fromProject || [...list]
      .filter((v) => String(v?.version_stage || "").trim().toLowerCase() === "final")
      .sort((a, b) => Number(b?.version_number || 0) - Number(a?.version_number || 0))[0] || null;
    if (!fallbackFinal) return "";
    return `Finalized content: ${getVersionLabel(fallbackFinal)} (v${fallbackFinal.version_number})`;
  }, [versions, currentProjectSummary]);
  const topBannerMessage = useMemo(() => {
    if (page === "settings") {
      return "";
    }
    if ((page === "artifacts" || page === "publish") && finalizedVersionBanner) {
      return finalizedVersionBanner;
    }
    return message;
  }, [page, finalizedVersionBanner, message]);

  const selectedVersion = useMemo(
    () => versions.find((v) => v.version_number === selectedVersionNumber) || null,
    [versions, selectedVersionNumber]
  );
  const nodeProgress = useMemo(() => {
    if (!isGenerating) return 0;
    const total = 3;
    const done = nodeAudit.filter((x) => x.status === "completed").length;
    return Math.min(100, Math.round((done / total) * 100));
  }, [isGenerating, nodeAudit]);
  const generatedArtifacts = useMemo(() => {
    if (!artifactOutput || !Array.isArray(artifactOutput.artifacts)) return [];
    return artifactOutput.artifacts;
  }, [artifactOutput]);
  const selectedGeneratedArtifact = generatedArtifacts[selectedArtifactTab] || null;
  const latestProjectImageStyleSeed = useMemo(
    () => pickLatestImageStyleSeed([...(Array.isArray(storedArtifacts) ? storedArtifacts : []), ...(Array.isArray(generatedArtifacts) ? generatedArtifacts : [])]),
    [storedArtifacts, generatedArtifacts]
  );
  const storedFormats = useMemo(() => {
    const byKind = artifactFormatsByKind && typeof artifactFormatsByKind === "object" ? artifactFormatsByKind : {};
    const preferredKindOrder = ["text", "image", "gif", "video", "audio"];
    const seen = new Set();
    const out = [];

    for (const kind of preferredKindOrder) {
      const formats = Array.isArray(byKind[kind]) ? byKind[kind] : [];
      for (const fmt of formats) {
        const normalized = String(fmt || "").trim();
        if (!normalized || seen.has(normalized)) continue;
        seen.add(normalized);
        out.push(normalized);
      }
    }

    for (const [kind, formats] of Object.entries(byKind)) {
      if (preferredKindOrder.includes(kind)) continue;
      for (const fmt of Array.isArray(formats) ? formats : []) {
        const normalized = String(fmt || "").trim();
        if (!normalized || seen.has(normalized)) continue;
        seen.add(normalized);
        out.push(normalized);
      }
    }

    return out;
  }, [artifactFormatsByKind]);
  const artifactFormatKindMap = useMemo(() => {
    const out = {};
    for (const [kind, formats] of Object.entries(artifactFormatsByKind || {})) {
      for (const fmt of Array.isArray(formats) ? formats : []) {
        const key = String(fmt || "").trim();
        if (!key) continue;
        out[key] = String(kind || "").trim();
      }
    }
    return out;
  }, [artifactFormatsByKind]);
  const artifactSelectedKinds = useMemo(() => {
    const seen = new Set();
    const out = [];
    for (const fmt of selectedArtifactFormats) {
      const kind = String(artifactFormatKindMap?.[fmt] || "").trim();
      if (!kind || seen.has(kind)) continue;
      seen.add(kind);
      out.push(kind);
    }
    return out;
  }, [selectedArtifactFormats, artifactFormatKindMap]);
  const filteredStoredArtifacts = useMemo(() => {
    if (!selectedStoredFormat) return [];
    return storedArtifacts.filter((a) => a?.format === selectedStoredFormat);
  }, [storedArtifacts, selectedStoredFormat]);
  const selectedStoredArtifact = filteredStoredArtifacts[selectedStoredArtifactTab] || null;
  const isArtifactEditActive = artifactEditMode !== "none";
  const approvedActiveVoiceProfileOptions = useMemo(() => {
    return vpCollections
      .filter((c) => c?.active_version && String(c.active_version.generation_status || "").toLowerCase() === "approved")
      .map((c) => {
        const active = c.active_version || {};
        const versionNo = active.version_no ?? "-";
        const name = String(c.voice_profile_name || c.voice_profile_id || "").trim();
        return {
          value: c.voice_profile_id,
          label: `${name} (active v${versionNo})`,
        };
      });
  }, [vpCollections]);
  const projectToneBase = useMemo(() => toneBaseFromProjectTone(form.tone_preference), [form.tone_preference]);
  const artifactSelectedFormatCards = useMemo(
    () => selectedArtifactFormats.map((fmt) => artifactFormatMeta(fmt)),
    [selectedArtifactFormats]
  );
  const artifactSelectedAdvancedFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => Object.prototype.hasOwnProperty.call(FORMAT_ADVANCED_DEFAULTS, x.key)),
    [artifactSelectedFormatCards]
  );
  const artifactSelectedVoiceProfilePreview = useMemo(
    () => normalizeVoiceProfilePreview(artifactStyleVoiceProfileDetail),
    [artifactStyleVoiceProfileDetail]
  );
  const artifactSelectedTextFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => artifactFormatKindMap?.[x.key] === "text"),
    [artifactSelectedFormatCards, artifactFormatKindMap]
  );
  const artifactSelectedImageFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => artifactFormatKindMap?.[x.key] === "image"),
    [artifactSelectedFormatCards, artifactFormatKindMap]
  );
  const artifactSelectedVideoFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => {
      const kind = artifactFormatKindMap?.[x.key];
      return kind === "video" || kind === "gif";
    }),
    [artifactSelectedFormatCards, artifactFormatKindMap]
  );
  const publishArtifactsById = useMemo(() => {
    const out = {};
    for (const a of Array.isArray(publishArtifacts) ? publishArtifacts : []) {
      const id = String(a?.artifact_id || "").trim();
      if (!id) continue;
      out[id] = a;
    }
    return out;
  }, [publishArtifacts]);
  const areRequiredPublishFieldsMapped = useMemo(() => {
    const schemaRows = Array.isArray(publishFieldSchema) ? publishFieldSchema : [];
    const requiredRows = schemaRows.filter((field) => !!field?.required);
    if (!requiredRows.length) return true;
    for (const field of requiredRows) {
      const fieldKey = String(field?.field_key || "").trim();
      if (!fieldKey) return false;
      const rows = Array.isArray(publishFieldMappings?.[fieldKey]) ? publishFieldMappings[fieldKey] : [];
      let hasValid = false;
      for (const row of rows) {
        const artifactId = String(row?.artifact_id || "").trim();
        const artifact = publishArtifactsById[artifactId] || null;
        const primaryPart = String(row?.primary_part || "").trim() || defaultPublishPartForArtifact(artifact);
        if (artifactId && primaryPart) {
          hasValid = true;
          break;
        }
      }
      if (!hasValid) return false;
    }
    return true;
  }, [publishFieldSchema, publishFieldMappings, publishArtifactsById]);
  const platformTargets = useMemo(
    () => uniqueStrings((publishPlatforms || []).map((p) => String(p || "").trim()).filter(Boolean)),
    [publishPlatforms]
  );
  const canGenerateContent = useMemo(() => {
    const topicTitle = String(form.topic_title || "").trim();
    const coreIdea = String(form.core_idea || "").trim();
    const targetAudience = String(form.target_audience_segment || "").trim();
    const tonePreference = String(form.tone_preference || "").trim();
    const voiceProfileId = String(form.voice_profile_id || "").trim();
    return !!(topicTitle && coreIdea && targetAudience && tonePreference && voiceProfileId);
  }, [form]);
  const canGenerateArtifactsNow = useMemo(() => {
    if (!selectedArtifactFormats.length) return false;
    const hasTextSelection = selectedArtifactFormats.some((fmt) => artifactFormatKindMap?.[fmt] === "text");
    const hasImageSelection = artifactSelectedKinds.includes("image");
    const hasVideoSelection = artifactSelectedKinds.includes("video") || artifactSelectedKinds.includes("gif");

    if (hasTextSelection) {
      if (artifactStyleSource === "manual" && !(artifactManualCoreVoice || "").trim()) return false;
      if (artifactStyleSource === "voice_profile" && !(artifactStyleVoiceProfileId || "").trim()) return false;
    }
    if (hasImageSelection) {
      if (!(artifactImageStyle?.theme || "").trim()) return false;
      if (!(artifactImageStyle?.subject_prompt || "").trim()) return false;
    }
    if (hasVideoSelection) {
      if (!(artifactVideoStyle?.theme || "").trim()) return false;
      if (!(artifactVideoStyle?.subject_prompt || "").trim()) return false;
    }
    return true;
  }, [
    selectedArtifactFormats,
    artifactFormatKindMap,
    artifactSelectedKinds,
    artifactStyleSource,
    artifactManualCoreVoice,
    artifactStyleVoiceProfileId,
    artifactImageStyle,
    artifactVideoStyle,
  ]);

  function renderStoredArtifactContent(artifact) {
    if (!artifact) return null;
    const fmt = String(artifact.format || "").trim();
    const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
    const body = typeof payload.body === "string" ? payload.body : "";
    const items = Array.isArray(payload.items) ? payload.items : [];
    const settings = payload?.settings && typeof payload.settings === "object" ? payload.settings : {};
    const hashtags = hashtagListFromArtifact(artifact);
    const topicTags = topicTagListFromArtifact(artifact);
    const assets = Array.isArray(payload.assets) ? payload.assets : [];
    const primaryAsset = assets[0] || null;
    const assetRef = String(primaryAsset?.uri || primaryAsset?.path || "").trim();
    const prompts = Array.isArray(payload.prompts) ? payload.prompts : [];
    const qcPromptRef = (() => {
      const fromSettingsUri = String(
        settings?.qc_prompt_uri || settings?.source_prompt_uri || settings?.prompt_uri || ""
      ).trim();
      if (fromSettingsUri) {
        return fromSettingsUri;
      }
      for (const p of prompts) {
        if (!p || typeof p !== "object") continue;
        const uri = String(p.uri || p.url || "").trim();
        if (uri && uri.toLowerCase().includes("/qc-prompts/")) {
          return uri;
        }
      }
      return null;
    })();
    const revisionLabel = artifact?.revision != null ? `v${artifact.revision}` : null;
    const psBits = [
      revisionLabel,
      assetRef ? `File/URL: ${assetRef}` : null,
      qcPromptRef ? `QC Prompt URL: ${qcPromptRef}` : null,
    ].filter(Boolean);

    if (["image_generation", "post_image", "thumbnail", "banner", "cover"].includes(fmt)) {
      const imageAsset = assets.find((a) => String(a?.mime_type || "").startsWith("image/")) || assets[0] || null;
      const imageSrc = imageSrcFromAsset(imageAsset);
      return (
        <div className="artifact-render">
          {imageSrc ? (
            <img className="artifact-image-preview" src={imageSrc} alt={artifact.title || "Generated image"} />
          ) : (
            <p className="note">
              Image preview unavailable in browser. URI: <code>{String(imageAsset?.uri || imageAsset?.path || "not available")}</code>
            </p>
          )}
          {imageAsset ? (
            <p className="note">Format: {imageAsset.format || "-"}{imageAsset.path ? ` | Path: ${imageAsset.path}` : ""}</p>
          ) : null}
          {psBits.length ? <p className="note artifact-ps-note">P.S. {psBits.join(" | ")}</p> : null}
        </div>
      );
    }

    if (["gif", "reel", "short_video", "video"].includes(fmt)) {
      const imageLikeAsset =
        assets.find((a) => String(a?.mime_type || "").startsWith("image/")) ||
        assets.find((a) => String(a?.format || "").toLowerCase() === "gif") ||
        null;
      const videoAsset = assets.find((a) => String(a?.mime_type || "").startsWith("video/")) || null;
      const imageSrc = imageSrcFromAsset(imageLikeAsset);
      const videoSrc = videoSrcFromAsset(videoAsset);
      const planItems = items
        .map((item) => ({
          seq: Number(item?.sequence || 0),
          text: String(item?.text || "").trim(),
          guidance: String(item?.guidance || "").trim(),
        }))
        .filter((x) => x.text || x.guidance)
        .sort((a, b) => a.seq - b.seq);

      return (
        <div className="artifact-render">
          {imageSrc ? (
            <img className="artifact-image-preview" src={imageSrc} alt={artifact.title || "Generated GIF"} />
          ) : videoSrc ? (
            <video className="artifact-video-preview" src={videoSrc} controls playsInline preload="metadata" />
          ) : (
            <p className="note">
              Media preview unavailable in browser. URI:{" "}
              <code>{String((videoAsset || imageLikeAsset)?.uri || (videoAsset || imageLikeAsset)?.path || "not available")}</code>
            </p>
          )}

          {planItems.length ? (
            <>
              <p className="note" style={{ marginTop: "10px", marginBottom: "6px" }}>Video plan</p>
              <div className="artifact-doc">
                {planItems.map((item, idx) => (
                  <p key={`${item.seq}-${idx}`} className="artifact-script-line">
                    <strong>{item.text || `Step ${idx + 1}`}</strong>
                    {item.guidance ? `: ${item.guidance}` : ""}
                  </p>
                ))}
              </div>
            </>
          ) : null}

          {psBits.length ? <p className="note artifact-ps-note">P.S. {psBits.join(" | ")}</p> : null}
        </div>
      );
    }

    if (fmt === "cta_variants") {
      const ctas = items
        .map((item) => ({ text: String(item?.text || "").trim(), seq: Number(item?.sequence || 0) }))
        .filter((x) => x.text)
        .sort((a, b) => a.seq - b.seq);
      return (
        <div className="artifact-render">
          <div className="artifact-cta-grid">
            {ctas.map((cta, idx) => (
              <button key={`${cta.seq}-${idx}`} type="button" className="secondary artifact-cta-button">
                {cta.text}
              </button>
            ))}
          </div>
          {psBits.length ? <p className="note artifact-ps-note">P.S. {psBits.join(" | ")}</p> : null}
        </div>
      );
    }

    if (fmt === "script_short") {
      const beats = items
        .map((item) => ({ text: String(item?.text || "").trim(), seq: Number(item?.sequence || 0) }))
        .filter((x) => x.text)
        .sort((a, b) => a.seq - b.seq);
      const targetDurationSec = Number(settings?.target_duration_sec || 0);
      return (
        <div className="artifact-render">
          {targetDurationSec > 0 ? (
            <p className="note" style={{ marginTop: "-2px", marginBottom: "10px" }}>
              Target duration: {targetDurationSec}s
            </p>
          ) : null}
          <div className="artifact-doc">
            {beats.map((beat, idx) => (
              <p key={`${beat.seq}-${idx}`} className="artifact-script-line">{beat.text}</p>
            ))}
          </div>
          {topicTags.length ? (
            <div className="artifact-hashtags">
              {topicTags.map((tag) => <span key={tag} className="artifact-hashtag">{tag}</span>)}
            </div>
          ) : null}
          {psBits.length ? <p className="note artifact-ps-note">P.S. {psBits.join(" | ")}</p> : null}
        </div>
      );
    }

    if (fmt === "blog" || fmt === "blog_long" || fmt === "newsletter") {
      return (
        <div className="artifact-render">
          <article className="artifact-doc">{body || "No content available."}</article>
          {topicTags.length ? (
            <div className="artifact-hashtags">
              {topicTags.map((tag) => <span key={tag} className="artifact-hashtag">{tag}</span>)}
            </div>
          ) : null}
          {psBits.length ? <p className="note artifact-ps-note">P.S. {psBits.join(" | ")}</p> : null}
        </div>
      );
    }

    if (fmt === "caption" || fmt === "post" || fmt === "x_post" || fmt === "linkedin_post" || fmt === "instagram_caption") {
      const socialTags = hashtags.length ? hashtags : topicTags;
      return (
        <div className="artifact-render">
          <div className="artifact-social">{body || "No content available."}</div>
          {socialTags.length ? (
            <div className="artifact-hashtags">
              {socialTags.map((tag) => <span key={tag} className="artifact-hashtag">{tag}</span>)}
            </div>
          ) : null}
          {psBits.length ? <p className="note artifact-ps-note">P.S. {psBits.join(" | ")}</p> : null}
        </div>
      );
    }

    return <pre className="content">{JSON.stringify(artifact, null, 2)}</pre>;
  }

async function refreshVersions(projectId, preferredVersion) {
    const data = await request("GET", `/api/v1/versions/${encodePathSegment(projectId)}`);
    const list = data?.versions || [];
    setVersions(list);
    if (preferredVersion && list.some((v) => v.version_number === preferredVersion)) {
      setSelectedVersionNumber(preferredVersion);
      return list;
    }
    const finalVersionFromProject = Number(currentProjectSummary?.final_version_number);
    if (Number.isFinite(finalVersionFromProject) && list.some((v) => v.version_number === finalVersionFromProject)) {
      setSelectedVersionNumber(finalVersionFromProject);
      return list;
    }
    const latestFinal = [...list]
      .filter((v) => String(v?.version_stage || "").trim().toLowerCase() === "final")
      .sort((a, b) => Number(b?.version_number || 0) - Number(a?.version_number || 0))[0] || null;
    const base = list.find((v) => v.version_kind === "base");
    const fallback = latestFinal || base || list[0] || null;
    setSelectedVersionNumber(fallback ? fallback.version_number : null);
    return list;
  }

  function persistAuthToken(token) {
    const next = token || "";
    setAuthToken(next);
    if (next) window.localStorage.setItem("cpublishr_token", next);
    else window.localStorage.removeItem("cpublishr_token");
  }

  async function openEditorialForProject(projectId) {
    const normalizedProjectId = String(projectId || "").trim();
    if (!normalizedProjectId) {
      setError("Project ID is required.");
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const versionsList = await refreshVersions(normalizedProjectId);
      setPage("editorial");
      if (Array.isArray(versionsList) && versionsList.length) {
        setMessage("Editorial content loaded.");
      } else {
        setMessage(`No saved versions found for project "${normalizedProjectId}".`);
      }
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function request(method, path, body) {
    return apiRequest(apiBaseUrl, method, path, body, authToken);
  }

  async function loadCurrentUser() {
    if (!authToken) {
      setCurrentUser(null);
      return;
    }
    try {
      const me = await request("GET", "/api/v1/auth/me");
      setCurrentUser(me || null);
    } catch {
      persistAuthToken("");
      setCurrentUser(null);
    }
  }

  async function loadUserProjects() {
    if (!authToken) {
      setUserProjects([]);
      return;
    }
    setIsProjectsLoading(true);
    try {
      const out = await request("GET", "/api/v1/projects/");
      const rows = Array.isArray(out?.projects) ? out.projects : [];
      setUserProjects(rows);
      const currentProjectId = String(form.project_id || "").trim();
      const hasCurrent = currentProjectId && rows.some((p) => p?.project_id === currentProjectId);
      if (!currentProjectId && rows[0]?.project_id) {
        setForm((prev) => ({ ...prev, project_id: rows[0].project_id }));
      } else if (!hasCurrent && !hasManuallyEditedProjectId && rows[0]?.project_id) {
        setForm((prev) => ({ ...prev, project_id: rows[0].project_id }));
      }
    } catch {
      setUserProjects([]);
    } finally {
      setIsProjectsLoading(false);
    }
  }

  async function onAuthSubmit() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      if (!authForm.password) {
        throw new Error("Password is required.");
      }
      if (!authForm.user_id.trim()) {
        throw new Error("User ID is required.");
      }
      if (authMode === "signup" && !authForm.email.trim()) {
        throw new Error("Email is required for signup.");
      }
      const path = authMode === "signup" ? "/api/v1/auth/signup" : "/api/v1/auth/login";
      const payload = authMode === "signup"
        ? { user_id: authForm.user_id.trim(), email: authForm.email.trim(), password: authForm.password }
        : { user_id: authForm.user_id.trim(), password: authForm.password };
      const out = await apiRequest(apiBaseUrl, "POST", path, payload, "");
      persistAuthToken(out?.access_token || "");
      setCurrentUser(out?.user || null);
      setAuthForm((prev) => ({ ...prev, password: "" }));
      setMessage("");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function onLogout() {
    persistAuthToken("");
    setCurrentUser(null);
    setUserProjects([]);
    setPage("setup");
    setVpCollections([]);
    setVpSelectedCollectionId("");
    setVpCollectionDetail(null);
    setVpSelectedVersionId("");
    setVpVersionDetail(null);
    setShowVpVersionControls(false);
    setShowVpCreateCollectionForm(false);
    setHasManuallyEditedProjectId(false);
    setIsCreatingNewProject(false);
    setMessage("Logged out.");
  }

  function onNewProjectIdChange(nextProjectId) {
    setHasManuallyEditedProjectId(true);
    setIsCreatingNewProject(true);
    setForm((prev) => ({ ...prev, project_id: nextProjectId }));
  }

  async function onSelectExistingProject(projectId) {
    const value = String(projectId || "").trim();
    if (!value) return;
    setHasManuallyEditedProjectId(true);
    setIsCreatingNewProject(false);
    setForm((prev) => ({ ...prev, project_id: value }));
    await openEditorialForProject(value);
  }

  function onCreateNewProject() {
    setHasManuallyEditedProjectId(true);
    setIsCreatingNewProject(true);
    setForm((prev) => ({ ...prev, project_id: "" }));
    setHasExistingContent(false);
    setShowGenerateSetupForm(true);
    setPage("setup");
  }

  function onSelectVpCollection(collectionId) {
    setVpSelectedCollectionId(collectionId);
    setShowVpVersionControls(false);
    setShowVpCreateCollectionForm(false);
  }

  async function vpRequest(method, path, body) {
    return apiRequest(apiBaseUrl, method, path, body, authToken);
  }

  async function loadVpCollections(preferredCollectionId = "") {
    if (!authToken) {
      setVpCollections([]);
      setVpSelectedCollectionId("");
      setVpCollectionDetail(null);
      setVpSelectedVersionId("");
      setVpVersionDetail(null);
      setShowVpVersionControls(false);
      setShowVpCreateCollectionForm(false);
      return;
    }
    const out = await vpRequest("GET", "/api/v1/voice-profiles/collections");
    const rows = Array.isArray(out?.collections) ? out.collections : [];
    setVpCollections(rows);
    const hasPreferred = preferredCollectionId && rows.some((x) => x.voice_profile_id === preferredCollectionId);
    const nextCollectionId = hasPreferred ? preferredCollectionId : rows[0]?.voice_profile_id || "";
    setVpSelectedCollectionId(nextCollectionId);

    const activeApproved = rows.find(
      (x) => x?.active_version && String(x.active_version.generation_status || "").toLowerCase() === "approved"
    );
    if (activeApproved) {
      setForm((prev) => ({ ...prev, voice_profile_id: activeApproved.voice_profile_id }));
    }
  }

  async function loadVpCollectionDetail(voiceProfileId) {
    if (!voiceProfileId || !authToken) {
      setVpCollectionDetail(null);
      setVpSelectedVersionId("");
      setVpVersionDetail(null);
      return;
    }
    const out = await vpRequest("GET", `/api/v1/voice-profiles/collections/${voiceProfileId}`);
    setVpCollectionDetail(out || null);
    const versions = Array.isArray(out?.versions) ? out.versions : [];
    const active = versions.find((v) => v.is_active);
    setVpSelectedVersionId(active?.voice_profile_version_id || versions[0]?.voice_profile_version_id || "");
  }

  async function loadVpVersionDetail(voiceProfileVersionId) {
    if (!voiceProfileVersionId || !authToken) {
      setVpVersionDetail(null);
      return;
    }
    const out = await vpRequest("GET", `/api/v1/voice-profiles/versions/${voiceProfileVersionId}`);
    setVpVersionDetail(out || null);
  }

  async function loadArtifactVoiceProfilePreview(voiceProfileId) {
    if (!voiceProfileId || !authToken) {
      setArtifactStyleVoiceProfileDetail(null);
      return;
    }
    setIsArtifactStyleVoiceProfileLoading(true);
    try {
      const detail = await vpRequest("GET", `/api/v1/voice-profiles/collections/${voiceProfileId}`);
      const versions = Array.isArray(detail?.versions) ? detail.versions : [];
      const preferred =
        versions.find((v) => v.is_active && String(v.generation_status || "").toLowerCase() === "approved")
        || versions.find((v) => v.is_active)
        || versions.find((v) => String(v.generation_status || "").toLowerCase() === "approved")
        || versions[0];
      if (!preferred?.voice_profile_version_id) {
        setArtifactStyleVoiceProfileDetail(null);
        return;
      }
      const versionDetail = await vpRequest("GET", `/api/v1/voice-profiles/versions/${preferred.voice_profile_version_id}`);
      setArtifactStyleVoiceProfileDetail(versionDetail || null);
    } catch {
      setArtifactStyleVoiceProfileDetail(null);
    } finally {
      setIsArtifactStyleVoiceProfileLoading(false);
    }
  }

  function updateArtifactToneNuance(field, value) {
    setArtifactToneNuance((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactAdvanced(formatKey, field, value) {
    setArtifactFormatAdvanced((prev) => ({
      ...prev,
      [formatKey]: {
        ...(prev?.[formatKey] || {}),
        [field]: value,
      },
    }));
  }

  function toggleArtifactAdvancedAngle(angle) {
    setArtifactFormatAdvanced((prev) => {
      const curr = new Set(prev?.cta_variants?.angles || []);
      if (curr.has(angle)) curr.delete(angle);
      else curr.add(angle);
      return {
        ...prev,
        cta_variants: {
          ...(prev?.cta_variants || {}),
          angles: Array.from(curr),
        },
      };
    });
  }

  function toggleArtifactAdvancedDrawer(formatKey) {
    setArtifactAdvancedOpen((prev) => ({ ...prev, [formatKey]: !prev?.[formatKey] }));
  }

  function updateArtifactImageStyle(field, value) {
    setArtifactImageStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactImageBrandColor(field, value) {
    setArtifactImageStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function addArtifactImageAvoidTag() {
    const tag = String(artifactImageAvoidInput || "").trim();
    if (!tag) return;
    setArtifactImageStyle((prev) => {
      const curr = Array.isArray(prev?.avoid) ? prev.avoid : [];
      const next = uniqueStrings([...curr, tag]);
      return { ...prev, avoid: next };
    });
    setArtifactImageAvoidInput("");
  }

  function removeArtifactImageAvoidTag(tagToRemove) {
    setArtifactImageStyle((prev) => ({
      ...prev,
      avoid: (Array.isArray(prev?.avoid) ? prev.avoid : []).filter((x) => x !== tagToRemove),
    }));
  }

  function updateArtifactVideoStyle(field, value) {
    setArtifactVideoStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactVideoBrandColor(field, value) {
    setArtifactVideoStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function addArtifactVideoAvoidTag() {
    const tag = String(artifactVideoAvoidInput || "").trim();
    if (!tag) return;
    setArtifactVideoStyle((prev) => {
      const curr = Array.isArray(prev?.avoid) ? prev.avoid : [];
      return { ...prev, avoid: uniqueStrings([...curr, tag]) };
    });
    setArtifactVideoAvoidInput("");
  }

  function removeArtifactVideoAvoidTag(tagToRemove) {
    setArtifactVideoStyle((prev) => ({
      ...prev,
      avoid: (Array.isArray(prev?.avoid) ? prev.avoid : []).filter((x) => x !== tagToRemove),
    }));
  }

  function updateArtifactIterateToneNuance(field, value) {
    setArtifactIterateToneNuance((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactIterateAdvanced(formatKey, field, value) {
    setArtifactIterateFormatAdvanced((prev) => ({
      ...prev,
      [formatKey]: {
        ...(prev?.[formatKey] || {}),
        [field]: value,
      },
    }));
  }

  function updateArtifactIterateImageStyle(field, value) {
    setArtifactIterateImageStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactIterateImageBrandColor(field, value) {
    setArtifactIterateImageStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function updateArtifactIterateVideoStyle(field, value) {
    setArtifactIterateVideoStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactIterateVideoBrandColor(field, value) {
    setArtifactIterateVideoStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function buildArtifactTextKindStyleSettings() {
    const toneBase = toneBaseFromProjectTone(form.tone_preference);
    const toneNuancePayload = {
      tone_base: toneBase,
      tone_nuance: {
        directness: clampInt(artifactToneNuance.directness, 0, 4, 2),
        warmth: clampInt(artifactToneNuance.warmth, 0, 4, 2),
        energy: clampInt(artifactToneNuance.energy, 0, 4, 2),
        authority: clampInt(artifactToneNuance.authority, 0, 4, 2),
      },
    };
    if (toneBase === "analytical") {
      toneNuancePayload.tone_nuance.rigor = clampInt(artifactToneNuance.rigor, 0, 4, 3);
      toneNuancePayload.tone_nuance.abstraction = clampInt(artifactToneNuance.abstraction, 0, 4, 2);
      toneNuancePayload.tone_nuance.framework_mode = String(artifactFrameworkMode || "light");
    }
    if (toneBase === "professional") {
      toneNuancePayload.tone_nuance.formality = clampInt(artifactToneNuance.formality, 0, 4, 3);
      toneNuancePayload.tone_nuance.diplomacy = clampInt(artifactToneNuance.diplomacy, 0, 4, 3);
    }
    if (toneBase === "conversational") {
      toneNuancePayload.tone_nuance.humor = String(artifactToneNuance.humor || "light");
      toneNuancePayload.tone_nuance.storyness = clampInt(artifactToneNuance.storyness, 0, 4, 2);
    }

    if (artifactStyleSource === "manual") {
      return {
        style_source: "manual",
        core_voice: (artifactManualCoreVoice || "").trim(),
        ...toneNuancePayload,
      };
    }

    return {
      style_source: "voice_profile",
      voice_profile_id: artifactStyleVoiceProfileId || form.voice_profile_id || "",
      voice_profile_preview: artifactSelectedVoiceProfilePreview || null,
      ...toneNuancePayload,
    };
  }

  function buildArtifactKindStyleSettings() {
    const selected = new Set(selectedArtifactFormats);
    const out = {};
    const hasTextSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "text");
    const hasImageSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "image");
    const hasVideoSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "video");
    const hasGifSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "gif");
    if (hasTextSelection) {
      out.text = buildArtifactTextKindStyleSettings();
    }
    if (hasImageSelection) {
      const avoid = uniqueStrings((artifactImageStyle?.avoid || []).map((x) => String(x || "").trim()).filter(Boolean));
      out.image = {
        theme: String(artifactImageStyle?.theme || "").trim(),
        subject_prompt: String(artifactImageStyle?.subject_prompt || "").trim(),
        avoid,
        medium: String(artifactImageStyle?.medium || "illustration"),
        texture: String(artifactImageStyle?.texture || "clean"),
        lighting: String(artifactImageStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactImageStyle?.palette_mode || "muted"),
        mood: String(artifactImageStyle?.mood || "premium"),
        focus_negative_space: String(artifactImageStyle?.focus_negative_space || "subject_centered"),
        output_fidelity: String(artifactImageStyle?.output_fidelity || "standard").toLowerCase(),
      };
      if (String(out.image.palette_mode) === "brand") {
        out.image.brand_colors = {
          primary: String(artifactImageStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactImageStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactImageStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactImageStyle?.brand_colors?.background || "").trim(),
        };
      }
    }
    if (hasVideoSelection || hasGifSelection) {
      const avoid = uniqueStrings((artifactVideoStyle?.avoid || []).map((x) => String(x || "").trim()).filter(Boolean));
      const videoPayload = {
        theme: String(artifactVideoStyle?.theme || "").trim(),
        subject_prompt: String(artifactVideoStyle?.subject_prompt || "").trim(),
        avoid,
        mood: String(artifactVideoStyle?.mood || "energetic"),
        lighting: String(artifactVideoStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactVideoStyle?.palette_mode || "muted"),
        output_fidelity: String(artifactVideoStyle?.output_fidelity || "standard").toLowerCase(),
        camera_motion: String(artifactVideoStyle?.camera_motion || "").trim(),
        energy_level: String(artifactVideoStyle?.energy_level || "medium"),
      };
      if (String(videoPayload.palette_mode) === "brand") {
        videoPayload.brand_colors = {
          primary: String(artifactVideoStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactVideoStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactVideoStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactVideoStyle?.brand_colors?.background || "").trim(),
        };
      }
      if (hasVideoSelection) out.video = { ...videoPayload };
      if (hasGifSelection) out.gif = { ...videoPayload };
    }
    return out;
  }

  function buildArtifactFormatStyleOverrides() {
    const selected = new Set(selectedArtifactFormats);
    const out = {};
    for (const fmt of selected) {
      const settings = artifactFormatAdvanced?.[fmt];
      if (!settings || typeof settings !== "object") continue;
      out[fmt] = { ...settings };
      if (fmt === "newsletter") {
        out[fmt].sections = clampInt(settings.sections, 3, 5, 4);
        out[fmt].takeaway_bullets = clampInt(settings.takeaway_bullets, 3, 6, 4);
      }
      if (fmt === "blog") {
        out[fmt].faq_count = clampInt(settings.faq_count, 0, 5, 3);
      }
      if (fmt === "script_short") {
        out[fmt].target_duration_sec = clampInt(settings.target_duration_sec, 15, 60, 30);
      }
      if (fmt === "cta_variants") {
        out[fmt].variant_count = clampInt(settings.variant_count, 7, 11, 7);
        out[fmt].angles = uniqueStrings(settings.angles || []);
      }
    }
    return out;
  }

  function getStoredArtifactSourceBlobPaths(artifact) {
    const assets = Array.isArray(artifact?.payload_json?.assets) ? artifact.payload_json.assets : [];
    return uniqueStrings(
      assets
        .map((a) => String(a?.blob_path || a?.uri || a?.path || "").trim())
        .filter(Boolean)
    );
  }

  function buildIterateKindStyleSettings(artifact) {
    const kind = String(artifact?.kind || "").trim().toLowerCase();
    if (!kind) return {};
    if (kind === "text") {
      const toneBase = toneBaseFromProjectTone(form.tone_preference);
      const toneNuancePayload = {
        tone_base: toneBase,
        tone_nuance: {
          directness: clampInt(artifactIterateToneNuance.directness, 0, 4, 2),
          warmth: clampInt(artifactIterateToneNuance.warmth, 0, 4, 2),
          energy: clampInt(artifactIterateToneNuance.energy, 0, 4, 2),
          authority: clampInt(artifactIterateToneNuance.authority, 0, 4, 2),
        },
      };
      if (toneBase === "analytical") {
        toneNuancePayload.tone_nuance.rigor = clampInt(artifactIterateToneNuance.rigor, 0, 4, 3);
        toneNuancePayload.tone_nuance.abstraction = clampInt(artifactIterateToneNuance.abstraction, 0, 4, 2);
        toneNuancePayload.tone_nuance.framework_mode = String(artifactIterateFrameworkMode || "light");
      }
      const manualCoreVoice = String(artifactIterateManualCoreVoice || "").trim();
      const textStyle = artifactIterateStyleSource === "voice_profile"
        ? {
          style_source: "voice_profile",
          voice_profile_id: (artifactIterateVoiceProfileId || form.voice_profile_id || "").trim(),
          voice_profile_preview: artifactSelectedVoiceProfilePreview || null,
        }
        : (manualCoreVoice
          ? { style_source: "manual", core_voice: manualCoreVoice }
          : {});
      return { text: { ...textStyle, ...toneNuancePayload } };
    }
    if (kind === "image") {
      const imagePayload = {
        medium: String(artifactIterateImageStyle?.medium || "illustration"),
        texture: String(artifactIterateImageStyle?.texture || "clean"),
        lighting: String(artifactIterateImageStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactIterateImageStyle?.palette_mode || "muted"),
        mood: String(artifactIterateImageStyle?.mood || "premium"),
        focus_negative_space: String(artifactIterateImageStyle?.focus_negative_space || "subject_centered"),
        output_fidelity: String(artifactIterateImageStyle?.output_fidelity || "standard").toLowerCase(),
      };
      if (imagePayload.palette_mode === "brand") {
        imagePayload.brand_colors = {
          primary: String(artifactIterateImageStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactIterateImageStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactIterateImageStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactIterateImageStyle?.brand_colors?.background || "").trim(),
        };
      }
      return { image: imagePayload };
    }
    if (kind === "video" || kind === "gif") {
      const videoPayload = {
        mood: String(artifactIterateVideoStyle?.mood || "energetic"),
        lighting: String(artifactIterateVideoStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactIterateVideoStyle?.palette_mode || "muted"),
        output_fidelity: String(artifactIterateVideoStyle?.output_fidelity || "standard").toLowerCase(),
        camera_motion: String(artifactIterateVideoStyle?.camera_motion || "").trim(),
        energy_level: String(artifactIterateVideoStyle?.energy_level || "medium"),
      };
      if (videoPayload.palette_mode === "brand") {
        videoPayload.brand_colors = {
          primary: String(artifactIterateVideoStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactIterateVideoStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactIterateVideoStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactIterateVideoStyle?.brand_colors?.background || "").trim(),
        };
      }
      return kind === "gif" ? { gif: videoPayload } : { video: videoPayload };
    }
    return {};
  }

  function buildIterateFormatStyleOverrides(artifact) {
    const fmt = String(artifact?.format || "").trim();
    if (!Object.prototype.hasOwnProperty.call(FORMAT_ADVANCED_DEFAULTS, fmt)) return {};
    const settings = artifactIterateFormatAdvanced?.[fmt];
    if (!settings || typeof settings !== "object") return {};
    const out = { [fmt]: { ...settings } };
    if (fmt === "newsletter") {
      out[fmt].sections = clampInt(settings.sections, 3, 5, 4);
      out[fmt].takeaway_bullets = clampInt(settings.takeaway_bullets, 3, 6, 4);
    }
    if (fmt === "blog") {
      out[fmt].faq_count = clampInt(settings.faq_count, 0, 5, 3);
    }
    if (fmt === "script_short") {
      out[fmt].target_duration_sec = clampInt(settings.target_duration_sec, 15, 60, 30);
    }
    if (fmt === "cta_variants") {
      out[fmt].variant_count = clampInt(settings.variant_count, 7, 11, 7);
      out[fmt].angles = uniqueStrings(settings.angles || []);
    }
    return out;
  }

  function toggleVpPlatform(platform) {
    const curr = new Set(vpCreateForm.platforms || []);
    if (curr.has(platform)) curr.delete(platform);
    else curr.add(platform);
    setVpCreateForm((prev) => ({ ...prev, platforms: Array.from(curr) }));
  }

  async function onVpCreateCollection() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const payload = {
        voice_profile_name: (vpCreateForm.voice_profile_name || "").trim(),
        platforms: vpCreateForm.platforms || [],
      };
      const out = await vpRequest("POST", "/api/v1/voice-profiles/collections", payload);
      const newId = out?.collection?.voice_profile_id || "";
      setVpCreateForm({ voice_profile_name: "", platforms: ["linkedin"] });
      await loadVpCollections(newId);
      setShowVpVersionControls(false);
      setShowVpCreateCollectionForm(false);
      setMessage("Voice profile collection created.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function updateVpDatasetRow(index, field, value) {
    setVpGenerateForm((prev) => {
      const rows = [...prev.datasets];
      rows[index] = { ...rows[index], [field]: value };
      return { ...prev, datasets: rows };
    });
  }

  function addVpDatasetRow() {
    setVpGenerateForm((prev) => ({
      ...prev,
      datasets: [...prev.datasets, { dataset_name: "", source_profile: "", blob_prefix: "", sample_scope_note: "" }],
    }));
  }

  function removeVpDatasetRow(index) {
    setVpGenerateForm((prev) => {
      if (prev.datasets.length <= 1) return prev;
      return { ...prev, datasets: prev.datasets.filter((_, i) => i !== index) };
    });
  }

  async function onVpGenerateVersion() {
    if (!vpSelectedCollectionId) {
      setError("Select a voice profile collection first.");
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    setIsVpGenerating(true);
    try {
      const payload = {
        intended_use: (vpGenerateForm.intended_use || "").trim() || null,
        datasets: vpGenerateForm.datasets.map((d) => ({
          dataset_name: (d.dataset_name || "").trim(),
          source_profile: (d.source_profile || "").trim() || null,
          blob_prefix: (d.blob_prefix || "").trim(),
          sample_scope_note: (d.sample_scope_note || "").trim() || null,
        })),
      };
      const out = await vpRequest(
        "POST",
        `/api/v1/voice-profiles/collections/${vpSelectedCollectionId}/versions/generate`,
        payload
      );
      const newVersionId = out?.generated_version?.version?.voice_profile_version_id || "";
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      if (newVersionId) setVpSelectedVersionId(newVersionId);
      setShowVpVersionControls(false);
      setMessage(`Voice profile version generated. Dataset entries written: ${out?.dataset_entries_written ?? 0}.`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setIsVpGenerating(false);
    }
  }

  async function onVpActivateVersion() {
    if (!vpSelectedVersionId) return;
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await vpRequest("POST", `/api/v1/voice-profiles/versions/${vpSelectedVersionId}/activate`, {});
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      await loadVpVersionDetail(vpSelectedVersionId);
      setMessage("Voice profile version activated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onVpUpdateStatus() {
    if (!vpSelectedVersionId) return;
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await vpRequest("POST", `/api/v1/voice-profiles/versions/${vpSelectedVersionId}/status`, {
        status: (vpStatusInput || "").trim(),
      });
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      await loadVpVersionDetail(vpSelectedVersionId);
      setMessage("Voice profile version status updated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function checkExistingContent(projectId) {
    const normalizedProjectId = (projectId || "").trim();
    const requestSeq = ++contentCheckSeqRef.current;
    if (!normalizedProjectId) {
      setHasExistingContent(false);
      setShowGenerateSetupForm(true);
      return;
    }
    setIsCheckingProjectData(true);
    try {
      const data = await request("GET", `/api/v1/versions/${encodePathSegment(normalizedProjectId)}`);
      if (requestSeq !== contentCheckSeqRef.current) return;
      const list = data?.versions || [];
      const exists = Array.isArray(list) && list.length > 0;
      setHasExistingContent(exists);
      setShowGenerateSetupForm(!exists);
    } catch {
      if (requestSeq !== contentCheckSeqRef.current) return;
      setHasExistingContent(false);
      setShowGenerateSetupForm(true);
    } finally {
      if (requestSeq !== contentCheckSeqRef.current) return;
      setIsCheckingProjectData(false);
    }
  }

  function applySelection(versionNumber) {
    const item = versions.find((v) => v.version_number === Number(versionNumber));
    setSelectedVersionNumber(Number(versionNumber));
    setWorkingContent(item?.content || "");
    setFeedbackPreviewContent("");
    setEditorMode("none");
  }

  function toggleTarget(target) {
    const current = new Set(form.distribution_targets);
    if (current.has(target)) current.delete(target);
    else current.add(target);
    setForm({ ...form, distribution_targets: Array.from(current) });
  }

  function buildTopicPayload() {
    const topicTitle = (form.topic_title || "").trim();
    const coreIdea = (form.core_idea || "").trim();
    const voiceProfileId = (form.voice_profile_id || "").trim();
    if (!topicTitle) {
      throw new Error("Topic Title is required.");
    }
    if (!coreIdea) {
      throw new Error("Core Idea is required.");
    }
    if (!voiceProfileId) {
      throw new Error("Voice Profile ID is required.");
    }
    return {
      project_id: (form.project_id || "").trim(),
      topic_title: topicTitle,
      core_idea: coreIdea,
      user_content: (form.user_content || "").trim() || null,
      target_audience: {
        primary_segment: form.target_audience_segment,
        notes: (form.target_audience_notes || "").trim() || null,
      },
      tone_preference: form.tone_preference,
      stance: form.stance || "balanced",
      audience_familiarity: form.audience_familiarity || null,
      detail_level: form.detail_level || null,
      primary_goal: form.primary_goal || null,
      desired_action: form.desired_action || null,
      voice_profile_id: voiceProfileId,
      distribution_targets: form.distribution_targets.length ? form.distribution_targets : null,
    };
  }

  function toggleArtifactFormat(format) {
    const current = new Set(selectedArtifactFormats);
    if (current.has(format)) current.delete(format);
    else current.add(format);
    setSelectedArtifactFormats(Array.from(current));
  }

  function toggleArtifactKind(kind) {
    const formats = orderArtifactFormats(kind, artifactFormatsByKind[kind] || []);
    const current = new Set(selectedArtifactFormats);
    const allSelected = formats.every((fmt) => current.has(fmt));
    if (allSelected) {
      formats.forEach((fmt) => current.delete(fmt));
    } else {
      formats.forEach((fmt) => current.add(fmt));
    }
    setSelectedArtifactFormats(Array.from(current));
  }

  async function onGenerateContent() {
    setError("");
    setMessage("");
    setIsGenerating(true);
    setBusy(true);
    setNodeAudit([]);
    setCanContinueToEditorial(false);
    try {
      const topicPayload = buildTopicPayload();
      setNodeAudit((prev) => [...prev, { node: "Node 0 - Topic Initialization", status: "running", output: null }]);
      const node0 = await request("POST", "/api/v1/projects/", topicPayload);
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 0 - Topic Initialization", status: "completed", output: node0 };
        return next;
      });

      setNodeAudit((prev) => [...prev, { node: "Node 1 - Research Trends", status: "running", output: null }]);
      const node1 = await request("POST", "/api/v1/workflows/nodes/research", {
        topic: topicPayload,
        persist_context: false,
      });
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 1 - Research Trends", status: "completed", output: node1 };
        return next;
      });

      setNodeAudit((prev) => [...prev, { node: "Node 2 - Master Content", status: "running", output: null }]);
      const node2 = await request("POST", "/api/v1/workflows/nodes/master", {
        topic: topicPayload,
        research: node1,
        persist_context: false,
        persist_versions: true,
      });
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 2 - Master Content", status: "completed", output: node2 };
        return next;
      });

      await refreshVersions(form.project_id);
      loadUserProjects().catch(() => {});
      setMessage("Node 0-2 completed. Review audit output below, then continue to editorial.");
      setCanContinueToEditorial(true);
    } catch (e) {
      setNodeAudit((prev) => {
        if (!prev.length) return prev;
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.status === "running") {
          next[next.length - 1] = { ...last, status: "failed", output: { error: e.message || String(e) } };
        }
        return next;
      });
      setError(e.message || String(e));
    } finally {
      setIsGenerating(false);
      setBusy(false);
    }
  }

  async function onOpenEditorialPage() {
    await openEditorialForProject(form.project_id);
  }

  async function onPatchKeywords(nextKeywords) {
    if (!selectedVersion) return;
    setError("");
    setBusy(true);
    try {
      await request(
        "PATCH",
        `/api/v1/versions/${form.project_id}/${selectedVersion.version_number}/keywords`,
        { keywords: nextKeywords }
      );
      await refreshVersions(form.project_id, selectedVersion.version_number);
      setKeywordsInput("");
      setMessage("Keywords updated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function requestVersionLabel(defaultLabel = "") {
    const raw = window.prompt("Enter a version name", defaultLabel || "");
    if (raw === null) return null;
    const label = raw.trim();
    if (!label) {
      setError("Version name is required to save.");
      return null;
    }
    return label;
  }

  async function saveDraftVersion({ content, versionLabel }) {
    if (!selectedVersion) return null;
    if (!(content || "").trim()) {
      setError("Content cannot be empty.");
      return null;
    }
    if (!(versionLabel || "").trim()) {
      setError("Please enter a version name before saving.");
      return null;
    }
    setError("");
    setBusy(true);
    try {
      const out = await request("POST", "/api/v1/workflows/nodes/editorial/save-inline", {
        project_id: form.project_id,
        source_version: selectedVersion.version_number,
        content: content.trim(),
        version_label: versionLabel.trim(),
      });
      await refreshVersions(form.project_id, out.draft_version);
      setWorkingContent(out?.content || content);
      setFeedbackPreviewContent("");
      setEditorMode("none");
      setMessage(`Saved "${versionLabel.trim()}" as v${out.draft_version}.`);
      return out;
    } catch (e) {
      setError(e.message || String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function onSaveInline() {
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Editorial draft");
    if (!versionLabel) return;
    await saveDraftVersion({
      content: workingContent,
      versionLabel,
    });
  }

  async function onFeedbackPreview() {
    if (!selectedVersion) return;
    if (!feedbackText.trim()) {
      setError("Feedback cannot be empty.");
      return;
    }
    setError("");
    setIsPreviewing(true);
    setBusy(true);
    try {
      const out = await request("POST", "/api/v1/workflows/nodes/editorial/feedback/preview", {
        project_id: form.project_id,
        source_version: selectedVersion.version_number,
        user_feedback: feedbackText,
      });
      setFeedbackPreviewContent(out?.preview_content || "");
      setMessage(`Preview generated from version v${selectedVersion.version_number}.`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsPreviewing(false);
      setBusy(false);
    }
  }

  async function onFinalizeSelected() {
    if (!selectedVersion) return;
    setError("");
    const prevPage = page;
    setMessage(`Finalizing version v${selectedVersion.version_number}...`);
    setPage("artifacts");
    setBusy(true);
    try {
      await request("POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: selectedVersion.version_number,
      });
      setMessage(`Finalized version v${selectedVersion.version_number}.`);
    } catch (e) {
      setError(e.message || String(e));
      setPage(prevPage);
    } finally {
      setBusy(false);
    }
  }

  async function onFinalizeFromInline() {
    if (!selectedVersion) return;
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Editorial draft");
    if (!versionLabel) return;
    const saved = await saveDraftVersion({
      content: workingContent,
      versionLabel,
    });
    if (!saved?.draft_version) return;
    setError("");
    const prevPage = page;
    setMessage(`Finalizing version v${saved.draft_version}...`);
    setPage("artifacts");
    setBusy(true);
    try {
      await request("POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: saved.draft_version,
      });
      setMessage(`Saved and finalized version v${saved.draft_version}.`);
      // Refresh versions asynchronously (do not block navigation).
      refreshVersions(form.project_id, saved.draft_version).catch(() => {});
    } catch (e) {
      setError(e.message || String(e));
      setPage(prevPage);
    } finally {
      setBusy(false);
    }
  }

  async function onSavePreview() {
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Iterated draft");
    if (!versionLabel) return;
    await saveDraftVersion({
      content: feedbackPreviewContent,
      versionLabel,
    });
  }

  async function onFinalizeFromPreview() {
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Iterated draft");
    if (!versionLabel) return;
    const saved = await saveDraftVersion({
      content: feedbackPreviewContent,
      versionLabel,
    });
    if (!saved?.draft_version) return;
    setError("");
    const prevPage = page;
    setMessage(`Finalizing version v${saved.draft_version}...`);
    setPage("artifacts");
    setBusy(true);
    try {
      await request("POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: saved.draft_version,
      });
      setMessage(`Saved and finalized version v${saved.draft_version}.`);
      // Refresh versions asynchronously (do not block navigation).
      refreshVersions(form.project_id, saved.draft_version).catch(() => {});
    } catch (e) {
      setError(e.message || String(e));
      setPage(prevPage);
    } finally {
      setBusy(false);
    }
  }

  function onCancelEditorialEdit() {
    setEditorMode("none");
    setFeedbackPreviewContent("");
    if (selectedVersion) {
      setWorkingContent(selectedVersion.content || "");
    }
  }

  async function onGenerateArtifacts() {
    if (!selectedArtifactFormats.length) {
      setError("Select at least one artifact format.");
      return;
    }
    if (!canGenerateArtifactsNow) {
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    setIsArtifactGenerating(true);
    setArtifactsViewMode("generate");
    setArtifactOutput(null);
    setSelectedArtifactTab(0);
    try {
      const styleSettingsByKind = buildArtifactKindStyleSettings();
      const formatOverrides = buildArtifactFormatStyleOverrides();
      const out = await request("POST", "/api/v1/artifacts/generate", {
        project_id: form.project_id,
        requested_formats: selectedArtifactFormats,
        revision_mode: "new_revision",
        style_settings_by_kind: styleSettingsByKind,
        style_settings_by_format: formatOverrides,
      });
      setArtifactOutput(out);
      setSelectedArtifactTab(0);
      const count = Array.isArray(out?.artifacts) ? out.artifacts.length : 0;
      setHasStoredArtifactsForProject(count > 0 || hasStoredArtifactsForProject);
      if (Array.isArray(out?.artifacts)) {
        const generatedFormats = out.artifacts.map((a) => String(a?.format || "").trim()).filter(Boolean);
        setStoredArtifactFormatsForProject((prev) => uniqueStrings([...(prev || []), ...generatedFormats]));
      }
      const genErrors = Array.isArray(out?.generation_errors) ? out.generation_errors : [];
      if (genErrors.length) {
        setError(genErrors.map((e) => `${e.format} failed - ${e.error}`).join("; "));
      }
      const errorSummary = genErrors.length
        ? " Warning: " + genErrors.map((e) => `${e.format} failed — ${e.error}`).join("; ")
        : "";
      setMessage(`${count} artifact(s) generated.${errorSummary} Loading your artifacts...`);
      setTimeout(() => onViewStoredArtifacts(), 1500);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setIsArtifactGenerating(false);
    }
  }

  async function onViewStoredArtifacts() {
    setError("");
    setMessage("");
    setBusy(true);
    setIsStoredArtifactsLoading(true);
    setArtifactsViewMode("stored");
    try {
      const out = await request("GET", `/api/v1/artifacts/${form.project_id}`);
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setStoredArtifacts(items);
      const formats = Array.from(new Set(items.map((a) => (a?.format || "").trim()).filter(Boolean))).sort();
      setStoredArtifactFormatsForProject(formats);
      setSelectedStoredFormat(formats[0] || "");
      setSelectedStoredArtifactTab(0);
      const count = Array.isArray(out?.artifacts) ? out.artifacts.length : 0;
      setHasStoredArtifactsForProject(count > 0);
      setMessage(`Loaded ${count} stored artifact(s).`);
    } catch (e) {
      setHasStoredArtifactsForProject(false);
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setIsStoredArtifactsLoading(false);
    }
  }

  async function checkStoredArtifactsAvailability(projectId) {
    const normalizedProjectId = (projectId || "").trim();
    const requestSeq = ++storedArtifactsCheckSeqRef.current;
    if (!authToken || !normalizedProjectId) {
      setHasStoredArtifactsForProject(false);
      setIsCheckingStoredArtifacts(false);
      setStoredArtifactFormatsForProject([]);
      return;
    }
    setIsCheckingStoredArtifacts(true);
    try {
      const out = await request("GET", `/api/v1/artifacts/${normalizedProjectId}`);
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setHasStoredArtifactsForProject(items.length > 0);
      setStoredArtifactFormatsForProject(
        uniqueStrings(items.map((a) => String(a?.format || "").trim()).filter(Boolean))
      );
    } catch {
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      setHasStoredArtifactsForProject(false);
      setStoredArtifactFormatsForProject([]);
    } finally {
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      setIsCheckingStoredArtifacts(false);
    }
  }

  async function loadPublishPlatforms() {
    if (!authToken) {
      setPublishPlatforms([]);
      setPublishSelectedPlatform("");
      return;
    }
    setIsPublishPlatformsLoading(true);
    try {
      const out = await request("GET", "/api/v1/publishing/platforms");
      const items = Array.isArray(out?.platforms) ? out.platforms.map((x) => String(x || "").trim()).filter(Boolean) : [];
      setPublishPlatforms(items);
      setPublishSelectedPlatform((prev) => (prev && items.includes(prev) ? prev : (items[0] || "")));
    } catch {
      setPublishPlatforms([]);
      setPublishSelectedPlatform("");
    } finally {
      setIsPublishPlatformsLoading(false);
    }
  }

  async function loadPublishFieldSchema(platform) {
    const p = String(platform || "").trim().toLowerCase();
    if (!authToken || !p) {
      setPublishFieldSchema([]);
      return;
    }
    setIsPublishFieldSchemaLoading(true);
    try {
      const out = await request("GET", `/api/v1/publishing/platforms/${p}/fields`);
      const fields = Array.isArray(out?.fields) ? out.fields : [];
      setPublishFieldSchema(fields);
      setPublishFieldMappings((prev) => {
        const next = {};
        for (const field of fields) {
          const key = String(field?.field_key || "").trim();
          if (!key) continue;
          next[key] = Array.isArray(prev?.[key]) ? prev[key] : [];
        }
        return next;
      });
    } catch {
      setPublishFieldSchema([]);
      setPublishFieldMappings({});
    } finally {
      setIsPublishFieldSchemaLoading(false);
    }
  }

  async function loadPublishArtifacts(projectId) {
    const pid = String(projectId || "").trim();
    if (!authToken || !pid) {
      setPublishArtifacts([]);
      return;
    }
    setIsPublishArtifactsLoading(true);
    try {
      const out = await request("GET", `/api/v1/artifacts/${pid}`);
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setPublishArtifacts(items);
    } catch {
      setPublishArtifacts([]);
    } finally {
      setIsPublishArtifactsLoading(false);
    }
  }

  async function browsePublishOutputLocations(pathValue = "") {
    setIsPublishBrowsingPaths(true);
    try {
      const query = String(pathValue || "").trim();
      const endpoint = query
        ? `/api/v1/publishing/output-path/browse?path=${encodeURIComponent(query)}`
        : "/api/v1/publishing/output-path/browse";
      const out = await request("GET", endpoint);
      setPublishBrowseCurrentPath(String(out?.current_path || ""));
      setPublishBrowseParentPath(String(out?.parent_path || ""));
      setPublishBrowseDirectories(Array.isArray(out?.directories) ? out.directories : []);
    } finally {
      setIsPublishBrowsingPaths(false);
    }
  }

  async function pickPublishOutputFolder() {
    setIsPublishPickingLocalPath(true);
    try {
      const out = await request("POST", "/api/v1/publishing/output-path/pick-local", {
        start_path: String(publishSaveOutputPath || publishBrowseCurrentPath || "").trim() || null,
      });
      const selected = String(out?.selected_path || "").trim();
      if (selected) {
        setPublishSaveOutputPath(selected);
        window.localStorage.setItem("cpublishr_publish_output_path", selected);
        await browsePublishOutputLocations(selected);
      }
    } finally {
      setIsPublishPickingLocalPath(false);
    }
  }

  function openSaveToPublishDialog() {
    setError("");
    setPublishSaveMessage("");
    setPublishSaveUserName("");
    setPublishBrowseCurrentPath("");
    setPublishBrowseParentPath("");
    setPublishBrowseDirectories([]);
    setShowPublishSaveDialog(true);
  }

  function closeSaveToPublishDialog() {
    if (busy || isPublishBrowsingPaths || isPublishPickingLocalPath) return;
    setShowPublishSaveDialog(false);
  }

  function buildSaveToPublishFieldMappings() {
    const schemaRows = Array.isArray(publishFieldSchema) ? publishFieldSchema : [];
    const out = [];
    for (const field of schemaRows) {
      const fieldKey = String(field?.field_key || "").trim();
      if (!fieldKey) continue;
      const rows = Array.isArray(publishFieldMappings?.[fieldKey]) ? publishFieldMappings[fieldKey] : [];
      const sources = [];
      let orderBase = 0;
      for (const row of rows) {
        const artifactId = String(row?.artifact_id || "").trim();
        const artifact = publishArtifactsById[artifactId] || null;
        const primaryPart = String(row?.primary_part || "").trim() || defaultPublishPartForArtifact(artifact);
        if (!artifactId || !primaryPart) continue;
        sources.push({
          artifact_id: artifactId,
          part: primaryPart,
          order: orderBase,
        });
        orderBase += 1;
        if (row?.include_tags) {
          sources.push({
            artifact_id: artifactId,
            part: "tags_json",
            order: orderBase,
          });
          orderBase += 1;
        }
      }
      if (sources.length) {
        out.push({ field_key: fieldKey, sources });
      }
    }
    return out;
  }

  async function onSaveToPublish() {
    setError("");
    setPublishSaveMessage("");
    const projectId = String(form.project_id || "").trim();
    const platform = String(publishSelectedPlatform || "").trim();
    if (!projectId) {
      setError("Project ID is required.");
      return;
    }
    if (!platform) {
      setError("Select a platform first.");
      return;
    }
    const userName = String(publishSaveUserName || "").trim();
    if (!userName) {
      setError("Name is required for Save to Publish.");
      return;
    }
    const outputPath = String(publishSaveOutputPath || "").trim();
    if (!outputPath) {
      setError("Output path is required. Enter a URL/path or pick a local folder.");
      return;
    }
    setBusy(true);
    try {
      const fieldMappings = buildSaveToPublishFieldMappings();
      const out = await request("POST", "/api/v1/publishing/save-to-publish", {
        project_id: projectId,
        platform,
        user_name: userName,
        output_path: outputPath,
        field_mappings: fieldMappings,
      });
      const savedPath = String(out?.output_path || "").trim();
      setPublishSaveMessage(savedPath ? `Saved to: ${savedPath}` : "Saved to publish.");
      window.localStorage.setItem("cpublishr_publish_output_path", outputPath);
      window.localStorage.setItem("cpublishr_publish_destination_mode", publishSaveDestinationMode);
      setShowPublishSaveDialog(false);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function addPublishSourceRow(fieldKey) {
    setPublishFieldMappings((prev) => {
      const key = String(fieldKey || "").trim();
      const rows = Array.isArray(prev?.[key]) ? prev[key] : [];
      return { ...prev, [key]: [...rows, makePublishSourceRow()] };
    });
  }

  function removePublishSourceRow(fieldKey, sourceId) {
    setPublishFieldMappings((prev) => {
      const key = String(fieldKey || "").trim();
      const rows = (Array.isArray(prev?.[key]) ? prev[key] : []).filter((r) => r?.source_id !== sourceId);
      return { ...prev, [key]: rows };
    });
  }

  function updatePublishSourceRow(fieldKey, sourceId, patch) {
    setPublishFieldMappings((prev) => {
      const key = String(fieldKey || "").trim();
      const rows = Array.isArray(prev?.[key]) ? prev[key] : [];
      return {
        ...prev,
        [key]: rows.map((row, idx) => {
          if (row?.source_id !== sourceId) return row;
          const next = { ...row, ...patch };
          next.order = idx;
          return next;
        }),
      };
    });
  }

  function resetArtifactEditPanel() {
    setArtifactEditMode("none");
    setIsArtifactEditing(false);
    setArtifactInlineText("");
    setArtifactIterateInstruction("");
  }

  function hydrateIterateStateFromArtifact(artifact) {
    const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
    const settings = payload?.settings && typeof payload.settings === "object" ? payload.settings : {};
    const styleByKind = settings?.style_settings_by_kind && typeof settings.style_settings_by_kind === "object"
      ? settings.style_settings_by_kind
      : {};
    const styleByFormat = settings?.style_settings_by_format && typeof settings.style_settings_by_format === "object"
      ? settings.style_settings_by_format
      : {};
    const kind = String(artifact?.kind || "").trim().toLowerCase();
    const fmt = String(artifact?.format || "").trim();

    if (kind === "text") {
      const textStyle = styleByKind?.text && typeof styleByKind.text === "object" ? styleByKind.text : {};
      const toneBase = toneBaseFromProjectTone(form.tone_preference);
      const nextTone = makeDefaultToneNuance(toneBase);
      const toneNuance = textStyle?.tone_nuance && typeof textStyle.tone_nuance === "object" ? textStyle.tone_nuance : {};
      setArtifactIterateToneNuance({ ...nextTone, ...toneNuance, tone_base: toneBase });
      setArtifactIterateFrameworkMode(String(toneNuance?.framework_mode || "light"));
      const source = String(textStyle?.style_source || "").trim().toLowerCase() === "voice_profile" ? "voice_profile" : "manual";
      setArtifactIterateStyleSource(source);
      setArtifactIterateVoiceProfileId(String(textStyle?.voice_profile_id || form.voice_profile_id || "").trim());
      setArtifactIterateManualCoreVoice(String(textStyle?.core_voice || "").trim());
    }

    if (kind === "image") {
      const imageStyle = styleByKind?.image && typeof styleByKind.image === "object" ? styleByKind.image : {};
      setArtifactIterateImageStyle((prev) => ({
        ...prev,
        ...imageStyle,
        brand_colors: {
          ...(prev?.brand_colors || {}),
          ...(imageStyle?.brand_colors && typeof imageStyle.brand_colors === "object" ? imageStyle.brand_colors : {}),
        },
      }));
    }

    if (kind === "video" || kind === "gif") {
      const videoStyleRaw = kind === "gif" ? styleByKind?.gif : styleByKind?.video;
      const videoStyle = videoStyleRaw && typeof videoStyleRaw === "object" ? videoStyleRaw : {};
      setArtifactIterateVideoStyle((prev) => ({
        ...prev,
        ...videoStyle,
        brand_colors: {
          ...(prev?.brand_colors || {}),
          ...(videoStyle?.brand_colors && typeof videoStyle.brand_colors === "object" ? videoStyle.brand_colors : {}),
        },
      }));
    }

    if (fmt && styleByFormat?.[fmt] && typeof styleByFormat[fmt] === "object") {
      setArtifactIterateFormatAdvanced((prev) => ({
        ...prev,
        [fmt]: {
          ...(prev?.[fmt] || {}),
          ...(styleByFormat[fmt] || {}),
        },
      }));
    }
  }

  function startInlineArtifactEdit(artifact) {
    const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
    const body = typeof payload?.body === "string" ? payload.body : "";
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const merged = body || items.map((x) => String(x?.text || "").trim()).filter(Boolean).join("\n");
    setArtifactInlineText(merged);
    setArtifactEditMode("inline");
  }

  function startIterateArtifactEdit(artifact) {
    setArtifactIterateInstruction("");
    hydrateIterateStateFromArtifact(artifact);
    setArtifactEditMode("iterate");
  }

  async function refreshStoredArtifactsAfterEdit() {
    const out = await request("GET", `/api/v1/artifacts/${form.project_id}`);
    const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
    setStoredArtifacts(items);
    const formats = uniqueStrings(items.map((a) => String(a?.format || "").trim()).filter(Boolean));
    setStoredArtifactFormatsForProject(formats);
    if (!formats.includes(selectedStoredFormat)) {
      setSelectedStoredFormat(formats[0] || "");
      setSelectedStoredArtifactTab(0);
    }
  }

  async function onSaveInlineArtifactEdit() {
    const artifactId = String(selectedStoredArtifact?.artifact_id || "").trim();
    if (!artifactId) return;
    setError("");
    setIsArtifactEditing(true);
    try {
      await request("POST", "/api/v1/artifacts/edit", {
        artifact_id: artifactId,
        mode: "inline",
        inline_content: String(artifactInlineText || ""),
      });
      await refreshStoredArtifactsAfterEdit();
      resetArtifactEditPanel();
      setMessage("Artifact updated inline.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsArtifactEditing(false);
    }
  }

  async function onIterateArtifactEdit() {
    const artifact = selectedStoredArtifact;
    const artifactId = String(artifact?.artifact_id || "").trim();
    if (!artifactId) return;
    if (!(artifactIterateInstruction || "").trim()) {
      setError("Edit Instruction is required for iterate.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const iterateKind = String(artifact?.kind || "").trim().toLowerCase();
    if (iterateKind === "text" && artifactIterateStyleSource === "voice_profile" && !(artifactIterateVoiceProfileId || form.voice_profile_id || "").trim()) {
      setError("Select a voice profile or switch to manual style.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setError("");
    setIsArtifactEditing(true);
    try {
      await request("POST", "/api/v1/artifacts/edit", {
        artifact_id: artifactId,
        mode: "iterate",
        edit_instruction: String(artifactIterateInstruction || "").trim(),
        style_settings_by_kind: buildIterateKindStyleSettings(artifact),
        style_settings_by_format: buildIterateFormatStyleOverrides(artifact),
        source_blob_paths: getStoredArtifactSourceBlobPaths(artifact),
      });
      await refreshStoredArtifactsAfterEdit();
      resetArtifactEditPanel();
      setMessage("Artifact iterated successfully.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsArtifactEditing(false);
    }
  }

  function startEditingArtifactTitle(artifact) {
    const id = String(artifact?.artifact_id || "").trim();
    if (!id) return;
    setEditingArtifactTitleId(id);
    setEditingArtifactTitleValue(String(artifact?.title || "").trim());
  }

  function cancelEditingArtifactTitle() {
    setEditingArtifactTitleId("");
    setEditingArtifactTitleValue("");
    setIsSavingArtifactTitle(false);
  }

  async function saveArtifactTitle(artifact) {
    const artifactId = String(artifact?.artifact_id || "").trim();
    if (!artifactId) return;
    if (!editingArtifactTitleId || editingArtifactTitleId !== artifactId) return;
    setError("");
    setIsSavingArtifactTitle(true);
    try {
      const out = await request("PATCH", `/api/v1/artifacts/item/${artifactId}/title`, {
        title: String(editingArtifactTitleValue || "").trim() || null,
      });
      const nextTitle = String(out?.title || "").trim() || null;
      setStoredArtifacts((prev) => (Array.isArray(prev) ? prev.map((a) => (
        a?.artifact_id === artifactId ? { ...a, title: nextTitle } : a
      )) : prev));
      setPublishArtifacts((prev) => (Array.isArray(prev) ? prev.map((a) => (
        a?.artifact_id === artifactId ? { ...a, title: nextTitle } : a
      )) : prev));
      setArtifactOutput((prev) => {
        if (!prev || !Array.isArray(prev.artifacts)) return prev;
        return {
          ...prev,
          artifacts: prev.artifacts.map((a) => (a?.artifact_id === artifactId ? { ...a, title: nextTitle } : a)),
        };
      });
      cancelEditingArtifactTitle();
    } catch (e) {
      setError(e.message || String(e));
      setIsSavingArtifactTitle(false);
    }
  }

  useEffect(() => {
    if (page !== "artifacts") return;
    setArtifactsViewMode("");
    setSelectedArtifactFormats([]);
    setArtifactGenerateStep("formats");
    setArtifactStyleKindPanel("text");
    resetArtifactEditPanel();
  }, [page]);

  useEffect(() => {
    resetArtifactEditPanel();
  }, [selectedStoredFormat, selectedStoredArtifactTab]);

  useEffect(() => {
    if (!isArtifactEditActive) return;
    autoResizeTextarea(artifactInlineTextareaRef.current);
    autoResizeTextarea(artifactIterateInstructionTextareaRef.current);
    autoResizeTextarea(artifactIterateVoiceStyleTextareaRef.current);
  }, [
    isArtifactEditActive,
    artifactInlineText,
    artifactIterateInstruction,
    artifactIterateManualCoreVoice,
    selectedStoredArtifact?.artifact_id,
  ]);

  useEffect(() => {
    if (page !== "editorial") return;
    if (editorMode === "inline") {
      autoResizeTextarea(editorialInlineTextareaRef.current);
    }
    if (editorMode === "iterate") {
      autoResizeTextarea(editorialFeedbackTextareaRef.current);
    }
  }, [page, editorMode, workingContent, feedbackText, selectedVersion?.version_number]);

  useEffect(() => {
    if (!artifactSelectedKinds.length) return;
    if (!artifactSelectedKinds.includes(artifactStyleKindPanel)) {
      setArtifactStyleKindPanel(artifactSelectedKinds[0]);
    }
  }, [artifactSelectedKinds, artifactStyleKindPanel]);

  useEffect(() => {
    const hasMediaStyleConsumer =
      artifactSelectedKinds.includes("image") || artifactSelectedKinds.includes("video") || artifactSelectedKinds.includes("gif");
    if (page !== "artifacts" || artifactsViewMode !== "generate" || artifactGenerateStep !== "style" || !hasMediaStyleConsumer) {
      return;
    }
    const projectId = String(form.project_id || "").trim();
    if (!projectId || !authToken) return;
    if (latestProjectImageStyleSeed) return;
    if (artifactStyleSeedFetchRef.current === projectId) return;
    artifactStyleSeedFetchRef.current = projectId;
    request("GET", `/api/v1/artifacts/${projectId}`)
      .then((out) => {
        const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
        setStoredArtifacts(items);
      })
      .catch(() => {});
  }, [
    page,
    artifactsViewMode,
    artifactGenerateStep,
    artifactSelectedKinds,
    form.project_id,
    authToken,
    latestProjectImageStyleSeed,
  ]);

  useEffect(() => {
    const seed = latestProjectImageStyleSeed;
    if (!seed) return;
    setArtifactImageStyle((prev) => {
      const next = { ...prev };
      let changed = false;
      if ((!String(prev?.palette_mode || "").trim() || String(prev?.palette_mode) === "muted") && seed.palette_mode) {
        next.palette_mode = seed.palette_mode;
        changed = true;
      }
      if ((!String(prev?.mood || "").trim() || String(prev?.mood) === "premium") && seed.mood) {
        next.mood = seed.mood;
        changed = true;
      }
      return changed ? next : prev;
    });
    setArtifactVideoStyle((prev) => {
      const next = { ...prev };
      let changed = false;
      if ((!String(prev?.palette_mode || "").trim() || String(prev?.palette_mode) === "muted") && seed.palette_mode) {
        next.palette_mode = seed.palette_mode;
        changed = true;
      }
      if ((!String(prev?.mood || "").trim() || String(prev?.mood) === "energetic") && seed.mood) {
        next.mood = seed.mood;
        changed = true;
      }
      return changed ? next : prev;
    });
  }, [latestProjectImageStyleSeed]);

  useEffect(() => {
    setArtifactToneNuance((prev) => {
      const nextBase = projectToneBase;
      if ((prev?.tone_base || "") === nextBase) return prev;
      const defaults = makeDefaultToneNuance(nextBase);
      return {
        ...defaults,
        directness: prev?.directness ?? defaults.directness,
        warmth: prev?.warmth ?? defaults.warmth,
        energy: prev?.energy ?? defaults.energy,
        authority: prev?.authority ?? defaults.authority,
      };
    });
    if (projectToneBase === "analytical") setArtifactFrameworkMode("light");
  }, [projectToneBase]);

  useEffect(() => {
    const next = (artifactStyleVoiceProfileId || form.voice_profile_id || "").trim();
    if (!artifactStyleVoiceProfileId && next) {
      setArtifactStyleVoiceProfileId(next);
    }
  }, [form.voice_profile_id, artifactStyleVoiceProfileId]);

  useEffect(() => {
    if (artifactStyleSource !== "voice_profile") return;
    if (!artifactStyleVoiceProfileId) {
      setArtifactStyleVoiceProfileDetail(null);
      return;
    }
    loadArtifactVoiceProfilePreview(artifactStyleVoiceProfileId).catch(() => {});
  }, [artifactStyleSource, artifactStyleVoiceProfileId, authToken]);

  useEffect(() => {
    if (!selectedVersion) return;
    setWorkingContent(selectedVersion.content || "");
    setFeedbackPreviewContent("");
  }, [selectedVersionNumber]);

  useEffect(() => {
    loadCurrentUser().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const projectId = (form.project_id || "").trim();
    checkExistingContent(projectId);
  }, [form.project_id, apiBaseUrl, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      setHasStoredArtifactsForProject(false);
      setIsCheckingStoredArtifacts(false);
      setStoredArtifactFormatsForProject([]);
      setPublishArtifacts([]);
      setPublishFieldSchema([]);
      setPublishFieldMappings({});
      setPublishPlatforms([]);
      setPublishSelectedPlatform("");
      return;
    }
    const projectId = (form.project_id || "").trim();
    setStoredArtifacts([]);
    setSelectedStoredFormat("");
    setSelectedStoredArtifactTab(0);
    setSelectedArtifactFormats([]);
    setArtifactsViewMode("");
    setArtifactGenerateStep("formats");
    setPublishArtifacts([]);
    setPublishFieldMappings({});
    checkStoredArtifactsAvailability(projectId);
  }, [form.project_id, apiBaseUrl, isAuthenticated, authToken]);

  useEffect(() => {
    if (!isAuthenticated) {
      setArtifactFormatsByKind({});
      return;
    }
    let ignore = false;
    async function loadArtifactFormats() {
      try {
        const out = await request("GET", "/api/v1/artifacts/catalog/formats");
        const byKind = out?.formats_by_kind && typeof out.formats_by_kind === "object" ? out.formats_by_kind : {};
        if (!ignore) setArtifactFormatsByKind(byKind);
      } catch {
        if (!ignore) setArtifactFormatsByKind({});
      }
    }
    loadArtifactFormats();
    return () => {
      ignore = true;
    };
  }, [apiBaseUrl, isAuthenticated, authToken]);

  useEffect(() => {
    if (!authToken) return;
    loadUserProjects().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!authToken) {
      setUserProjects([]);
      return;
    }
    loadVpCollections().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!authToken) return;
    loadPublishPlatforms().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!authToken || page !== "publish") return;
    loadPublishArtifacts(form.project_id).catch(() => {});
  }, [authToken, apiBaseUrl, page, form.project_id]);

  useEffect(() => {
    if (!authToken || page !== "publish") return;
    loadPublishFieldSchema(publishSelectedPlatform).catch(() => {});
  }, [authToken, apiBaseUrl, page, publishSelectedPlatform]);

  useEffect(() => {
    if (!authToken) return;
    loadVpCollectionDetail(vpSelectedCollectionId).catch(() => {});
  }, [vpSelectedCollectionId, authToken]);

  useEffect(() => {
    if (!authToken) return;
    loadVpVersionDetail(vpSelectedVersionId).catch(() => {});
  }, [vpSelectedVersionId, authToken]);

  useEffect(() => {
    if (!approvedActiveVoiceProfileOptions.length) return;
    const hasCurrent = approvedActiveVoiceProfileOptions.some((x) => x.value === form.voice_profile_id);
    if (!hasCurrent) {
      setForm((prev) => ({ ...prev, voice_profile_id: approvedActiveVoiceProfileOptions[0].value }));
    }
  }, [approvedActiveVoiceProfileOptions]);

  useEffect(() => {
    if (!platformTargets.length) {
      setForm((prev) => ({ ...prev, distribution_targets: [] }));
      setVpCreateForm((prev) => ({ ...prev, platforms: [] }));
      return;
    }
    setForm((prev) => {
      const current = Array.isArray(prev.distribution_targets) ? prev.distribution_targets : [];
      const filtered = current.filter((x) => platformTargets.includes(String(x || "").trim()));
      return { ...prev, distribution_targets: filtered };
    });
    setVpCreateForm((prev) => {
      const current = Array.isArray(prev.platforms) ? prev.platforms : [];
      const filtered = current.filter((x) => platformTargets.includes(String(x || "").trim()));
      return { ...prev, platforms: filtered.length ? filtered : [platformTargets[0]] };
    });
  }, [platformTargets]);

  const showWorkflowRegion = !isAuthenticated || (page !== "settings" && page !== "projects");

  return (
    <>
      <div className="top-banner">
        <div className="container top-banner-inner">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div className="top-banner-brand">
              <img
                src={publishrLogo}
                alt="Publishr logo"
                className="top-banner-logo"
              />
            </div>
            {isAuthenticated ? (
              <div className="top-banner-actions">
                <div className="row top-banner-buttons">
                  {(page !== "projects" && page !== "settings") ? (
                    <button className="secondary" disabled={busy} onClick={() => setPage("projects")}>Projects</button>
                  ) : null}
                  {page === "settings" ? (
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => {
                        if (isExistingProjectFlow) {
                          onOpenEditorialPage().catch(() => {});
                          return;
                        }
                        setPage("setup");
                      }}
                    >
                      Back to Workflow
                    </button>
                  ) : null}
                  {page !== "settings" ? (
                    <button className="secondary" disabled={busy} onClick={() => setPage("settings")}>Settings</button>
                  ) : null}
                  <button className="secondary" disabled={busy} onClick={onLogout}>Logout</button>
                </div>
                <span className="note top-banner-user">User ID: {currentUser?.user_id || "-"}</span>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="container">
        {isAuthenticated && page === "projects" ? (
          <div className="card">
            <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
              <h3 style={{ margin: 0 }}>Created Projects</h3>
              <button className="secondary" disabled={busy} onClick={onCreateNewProject}>+ Create New Project</button>
            </div>
            {isProjectsLoading ? <p className="note">Loading projects...</p> : null}
            {!isProjectsLoading && userProjects.length === 0 ? <p className="note">No projects found.</p> : null}
            <div className="row">
              {userProjects.map((p) => {
                const projectId = String(p?.project_id || "").trim();
                if (!projectId) return null;
                return (
                  <button
                    key={`project-list-${projectId}`}
                    className={form.project_id === projectId ? "primary" : "secondary"}
                    disabled={busy}
                    onClick={() => onSelectExistingProject(projectId)}
                  >
                    {projectId}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {(showWorkflowRegion || topBannerMessage || error || isGenerating || isArtifactGenerating || isStoredArtifactsLoading) ? (
          <div className="card">
            {showWorkflowRegion ? (
              <>
                <p className="note">Lightweight React interface for Node 0-3 flow with editorial actions.</p>
                <div className="grid two">
          <div>
            <label>Backend Base URL</label>
            <input value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} />
          </div>
          {!isAuthenticated ? (
            <>
              <div>
                <label>Auth Mode</label>
                <div className="row">
                  <button className={authMode === "login" ? "primary" : "secondary"} disabled={busy} onClick={() => setAuthMode("login")}>Login</button>
                  <button className={authMode === "signup" ? "primary" : "secondary"} disabled={busy} onClick={() => setAuthMode("signup")}>Signup</button>
                </div>
              </div>
              <div>
                <label>User ID</label>
                <input value={authForm.user_id} onChange={(e) => setAuthForm({ ...authForm, user_id: e.target.value })} />
              </div>
              {authMode === "signup" ? (
                <div>
                  <label>Email</label>
                  <input value={authForm.email} onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })} />
                </div>
              ) : null}
              <div>
                <label>Password</label>
                <input type="password" value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} />
              </div>
              <div>
                <label>Authenticate</label>
                <button className="primary" disabled={busy} onClick={onAuthSubmit}>
                  {busy ? "Please wait..." : authMode === "signup" ? "Sign Up" : "Login"}
                </button>
              </div>
            </>
          ) : (
            <>
              <div>
                <label>User</label>
                <p className="note">{currentUser?.user_id || "-"} ({currentUser?.email || "-"})</p>
              </div>
              <div>
                <label>Project ID</label>
                <input
                  value={form.project_id}
                  onChange={(e) => onNewProjectIdChange(e.target.value)}
                  placeholder="Enter a new project ID"
                />
                {page === "setup" && isProjectsLoading ? (
                  <p className="note" style={{ marginTop: "6px" }}>Loading your projects...</p>
                ) : null}
                {page === "setup" && hasExistingContent ? (
                  <div className="row" style={{ marginTop: "8px" }}>
                    <button
                      type="button"
                      className="primary"
                      disabled={busy || isCheckingProjectData || !canGenerateContent}
                      onClick={() => setShowGenerateSetupForm(true)}
                    >
                      Generate Content
                    </button>
                  </div>
                ) : null}
                {page === "setup" && isCheckingProjectData ? (
                  <p className="note" style={{ marginTop: "6px" }}>Checking project data...</p>
                ) : null}
              </div>
              <div>
                <label>Workflow Pages</label>
                <div className="row">
                  {!isExistingProjectFlow ? (
                    <button className={page === "setup" ? "primary" : "secondary"} disabled={busy} onClick={() => setPage("setup")}>Setup</button>
                  ) : null}
                  <button className={page === "editorial" ? "primary" : "secondary"} disabled={busy} onClick={onOpenEditorialPage}>Editorial</button>
                  <button className={page === "artifacts" ? "primary" : "secondary"} disabled={busy} onClick={() => setPage("artifacts")}>Artifacts</button>
                  <button className={page === "publish" ? "primary" : "secondary"} disabled={busy} onClick={() => setPage("publish")}>Publish</button>
                </div>
              </div>
              </>
            )}
            </div>
            </>
          ) : null}
            {topBannerMessage ? <div className="status ok">{topBannerMessage}</div> : null}
            {error ? <div className="status warn">{error}</div> : null}
            {(isGenerating || isArtifactGenerating || isStoredArtifactsLoading) ? (
              <div style={{ marginTop: "10px" }}>
                <div className="progress-label">
                  {isGenerating
                    ? `Generating content (Node 0-2): ${nodeProgress}%`
                    : (isArtifactGenerating ? "Generating artifacts..." : "Loading stored artifacts...")}
                </div>
                {isArtifactGenerating && selectedArtifactFormats.some((f) => ["post_image","thumbnail","banner","cover"].includes(f)) && (
                  <div style={{ fontSize: "0.82em", color: "#888", marginTop: "4px" }}>
                    Image and video generation may take a while — please hang on.
                  </div>
                )}
                <div className="progress-track">
                  <div
                    className={`progress-fill ${isGenerating ? "" : "indeterminate"}`}
                    style={isGenerating ? { width: `${nodeProgress}%` } : { width: "35%" }}
                  />
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

      {isAuthenticated && page === "setup" && showGenerateSetupForm && (
        <div className="card">
          <h2>Generate Content</h2>
          <div className="grid two">
            <div>
              <LabelWithTooltip
                text="Topic Title"
                required
                tooltip="A short headline for your post idea. Keep it simple and specific—this is used to name and organize your content."
              />
              <input value={form.topic_title} onChange={(e) => setForm({ ...form, topic_title: e.target.value })} placeholder={TOPIC_TITLE_SUGGESTION} />
            </div>
            <div>
              <LabelWithTooltip
                text="Core Idea"
                required
                tooltip="The one-sentence point you want to make. If someone reads only this, they should understand your main message."
              />
              <input value={form.core_idea} onChange={(e) => setForm({ ...form, core_idea: e.target.value })} placeholder={CORE_IDEA_SUGGESTION} />
            </div>
            <div>
              <LabelWithTooltip
                text="Target Audience"
                required
                tooltip="Who you’re writing for. Pick the closest match—this helps choose the right language, examples, and assumptions."
              />
              <select
                value={form.target_audience_segment}
                onChange={(e) => setForm({ ...form, target_audience_segment: e.target.value })}
              >
                {AUDIENCE_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Target Audience Notes"
                tooltip="Optional. Add specifics about your audience (role, industry, constraints). The more specific this is, the more accurate the output will be."
              />
              <input
                value={form.target_audience_notes}
                onChange={(e) => setForm({ ...form, target_audience_notes: e.target.value })}
                placeholder="Optional specifics for audience context"
              />
            </div>
            <div>
              <LabelWithTooltip
                text="Audience Familiarity"
                tooltip={"How familiar your audience is with this topic.\nNew: new to the topic\nSomewhat familiar: knows basics\nVery familiar: deep understanding"}
              />
              <select value={form.audience_familiarity} onChange={(e) => setForm({ ...form, audience_familiarity: e.target.value })}>
                {AUDIENCE_FAMILIARITY_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Detail Level"
                tooltip={"How detailed you want the content.\nQuick take: summary\nPractical: actionable depth\nDeep dive: thorough coverage with nuances"}
              />
              <select value={form.detail_level} onChange={(e) => setForm({ ...form, detail_level: e.target.value })}>
                {DETAIL_LEVEL_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Tone Preference"
                required
                tooltip="The “voice” of the writing—how it should sound. Example: conversational, formal, witty, bold, etc."
              />
              <select value={form.tone_preference} onChange={(e) => setForm({ ...form, tone_preference: e.target.value })}>
                {TONE_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Stance"
                tooltip={"The point of view you want to take.\nSupportive: agree/advocate\nContrarian: challenge the common view\nBalanced: show both sides and conclude"}
              />
              <select value={form.stance} onChange={(e) => setForm({ ...form, stance: e.target.value || "balanced" })}>
                {STANCE_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Primary Goal"
                tooltip="What you want this content to achieve. Example: educate, entertain, promote something, start a discussion, or drive sign-ups."
              />
              <select value={form.primary_goal} onChange={(e) => setForm({ ...form, primary_goal: e.target.value })}>
                {PRIMARY_GOAL_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Desired Action"
                tooltip="What you want people to do after reading. Example: comment, share, follow, click a link, DM you, subscribe, or buy."
              />
              <select value={form.desired_action} onChange={(e) => setForm({ ...form, desired_action: e.target.value })}>
                {DESIRED_ACTION_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <LabelWithTooltip
                text="User Content"
                tooltip="Any raw notes you already have - bullets, a rough draft, links, or context. The more specific this is, the more accurate the output will be."
              />
              <textarea
                ref={userContentTextareaRef}
                value={form.user_content || ""}
                onFocus={(e) => autoResizeTextarea(e.target)}
                onChange={(e) => {
                  setForm({ ...form, user_content: e.target.value });
                  autoResizeTextarea(e.target);
                }}
                placeholder={USER_CONTENT_SUGGESTION}
              />
            </div>
            <div>
              <LabelWithTooltip
                text="Voice Profile"
                required
                tooltip="Select from approved active voice profiles by name. The mapped voice_profile_id is sent to backend."
              />
              <select
                value={form.voice_profile_id || ""}
                onChange={(e) => setForm({ ...form, voice_profile_id: e.target.value })}
              >
                <option value="">Select approved active voice profile</option>
                {approvedActiveVoiceProfileOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              {form.voice_profile_id ? (
                <p className="note" style={{ marginTop: "6px" }}>Selected voice_profile_id: {form.voice_profile_id}</p>
              ) : (
                <p className="note" style={{ marginTop: "6px" }}>No approved active voice profile selected.</p>
              )}
            </div>
            <div>
              <LabelWithTooltip
                text="Distribution Targets"
                tooltip="Where you might publish this. This doesn’t change the core idea—just helps us prepare formats that fit those platforms later."
              />
              <div className="row">
                {platformTargets.map((t) => (
                  <label key={t} className="tag">
                    <input
                      type="checkbox"
                      checked={form.distribution_targets.includes(t)}
                      onChange={() => toggleTarget(t)}
                      style={{ width: "auto", marginRight: "6px" }}
                    />
                    {t}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="row" style={{ marginTop: "12px" }}>
            <button
              type="button"
              className="primary"
              disabled={busy || isCheckingProjectData || !canGenerateContent}
              onClick={onGenerateContent}
            >
              {isGenerating ? "Generating..." : "Generate Content"}
            </button>
            {canContinueToEditorial ? (
              <button className="secondary" disabled={busy} onClick={() => setPage("editorial")}>
                Continue to Editorial
              </button>
            ) : null}
          </div>
          {(isGenerating || nodeAudit.length > 0) ? (
            <div style={{ marginTop: "14px" }}>
              <h3>Workflow Audit (Node 0-2)</h3>
              <div className="chat">
                {nodeAudit.map((entry, idx) => (
                  <div key={`${entry.node}-${idx}`} className="msg">
                    <div className="who row" style={{ justifyContent: "space-between" }}>
                      <span>{entry.node}</span>
                      <span className={`audit-status ${entry.status || "running"}`}>{entry.status}</span>
                    </div>
                    {entry.output ? (
                      <pre className="content" style={{ marginTop: "6px", maxHeight: "220px" }}>
                        {JSON.stringify(entry.output, null, 2)}
                      </pre>
                    ) : (
                      <div className="note">Running...</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {isAuthenticated && page === "settings" && (
        <>
          <div className="card">
            <h2 style={{ marginBottom: 0 }}>Voice Profile Settings</h2>
            {!authToken ? (
              <p className="note">Login first to access voice profile APIs.</p>
            ) : null}
          </div>

          <div className="card">
            <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
              <h3 style={{ margin: 0 }}>Collections</h3>
              {showVpCreateCollectionForm ? (
                <button
                  className="secondary"
                  disabled={busy || !authToken}
                  onClick={() => {
                    setShowVpCreateCollectionForm(false);
                    setVpCreateForm({ voice_profile_name: "", platforms: ["linkedin"] });
                  }}
                >
                  Cancel
                </button>
              ) : (
                <button className="secondary" disabled={busy || !authToken} onClick={() => setShowVpCreateCollectionForm(true)}>Create Collection</button>
              )}
            </div>
            {showVpCreateCollectionForm ? (
              <>
                <div className="grid two">
                  <div>
                    <label>Collection Name</label>
                    <input
                      value={vpCreateForm.voice_profile_name}
                      onChange={(e) => setVpCreateForm((prev) => ({ ...prev, voice_profile_name: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label>Platforms</label>
                    <div className="row">
                      {platformTargets.map((p) => (
                        <label key={`vp-platform-${p}`} className="tag">
                          <input
                            type="checkbox"
                            checked={(vpCreateForm.platforms || []).includes(p)}
                            onChange={() => toggleVpPlatform(p)}
                            style={{ width: "auto", marginRight: "6px" }}
                          />
                          {p}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="row" style={{ marginTop: "10px" }}>
                  <button className="primary" disabled={busy || !authToken} onClick={onVpCreateCollection}>Create Collection</button>
                </div>
              </>
            ) : (
              <>
                {vpCollections.length === 0 ? <p className="note">No voice profile collections found.</p> : null}
                <div className="row">
                  {vpCollections.map((c) => (
                    <button
                      key={c.voice_profile_id}
                      className={vpSelectedCollectionId === c.voice_profile_id ? "primary" : "secondary"}
                      onClick={() => onSelectVpCollection(c.voice_profile_id)}
                    >
                      {c.voice_profile_name}
                    </button>
                  ))}
                </div>
                {vpSelectedCollectionId ? (
                  <p className="note" style={{ marginTop: "8px" }}>Selected collection id: {vpSelectedCollectionId}</p>
                ) : null}
              </>
            )}
          </div>

          {vpSelectedCollectionId && !showVpVersionControls ? (
            <div className="card">
              <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
                <h3 style={{ margin: 0 }}>Generate Voice Profile Version</h3>
                <button className="secondary" disabled={busy} onClick={() => setShowVpVersionControls(true)}>View existing</button>
              </div>
              <div>
                <label>Intended Use</label>
                <input
                  value={vpGenerateForm.intended_use}
                  onChange={(e) => setVpGenerateForm((prev) => ({ ...prev, intended_use: e.target.value }))}
                  placeholder="drafting / analysis / coaching"
                />
              </div>
              {(vpGenerateForm.datasets || []).map((row, idx) => (
                <div key={`vp-ds-${idx}`} className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <h3 style={{ marginBottom: 0 }}>Dataset {idx + 1}</h3>
                    <button className="danger" onClick={() => removeVpDatasetRow(idx)} disabled={vpGenerateForm.datasets.length <= 1}>Remove</button>
                  </div>
                  <div className="grid two" style={{ marginTop: "8px" }}>
                    <div>
                      <label>Dataset Name</label>
                      <input value={row.dataset_name || ""} onChange={(e) => updateVpDatasetRow(idx, "dataset_name", e.target.value)} />
                    </div>
                    <div>
                      <label>Source Profile (optional)</label>
                      <input value={row.source_profile || ""} onChange={(e) => updateVpDatasetRow(idx, "source_profile", e.target.value)} />
                    </div>
                    <div>
                      <label>Blob Prefix</label>
                      <input
                        value={row.blob_prefix || ""}
                        onChange={(e) => updateVpDatasetRow(idx, "blob_prefix", e.target.value)}
                        placeholder="user_id/dataset_name/ (or full blob URL)"
                      />
                    </div>
                  </div>
                  <div style={{ marginTop: "8px" }}>
                    <label>Sample Scope Note (optional)</label>
                    <textarea value={row.sample_scope_note || ""} onChange={(e) => updateVpDatasetRow(idx, "sample_scope_note", e.target.value)} />
                  </div>
                </div>
              ))}
              <div className="row" style={{ marginTop: "10px" }}>
                <button className="secondary" disabled={busy || !authToken} onClick={addVpDatasetRow}>Add Another Dataset</button>
                <button className="primary" disabled={busy || !authToken || !vpSelectedCollectionId} onClick={onVpGenerateVersion}>
                  {isVpGenerating ? "Generating Version..." : "Generate Version"}
                </button>
              </div>
              <p className="note" style={{ marginTop: "8px" }}>
                Dataset ID is system-generated by backend. Add another dataset only if one version should learn from multiple sources.
              </p>
              <p className="note" style={{ marginTop: "6px" }}>
                Blob Prefix should point inside container `profile-entries` (for example `ckashyap/Top_Posts/`).
              </p>
              {isVpGenerating ? (
                <div style={{ marginTop: "10px" }}>
                  <div className="progress-label">Generating voice profile version...</div>
                  <div className="progress-track">
                    <div className="progress-fill indeterminate" style={{ width: "35%" }} />
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {vpSelectedCollectionId && showVpVersionControls ? (
            <div className="card">
              <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
                <h3 style={{ margin: 0 }}>Version Controls</h3>
                <button className="secondary" disabled={busy} onClick={() => setShowVpVersionControls(false)}>Back to Generate</button>
              </div>
              {!vpCollectionDetail?.versions?.length ? <p className="note">No versions available for selected collection.</p> : null}
              <div className="row">
                {(vpCollectionDetail?.versions || []).map((v) => (
                  <button
                    key={v.voice_profile_version_id}
                    className={vpSelectedVersionId === v.voice_profile_version_id ? "primary" : "secondary"}
                    onClick={() => setVpSelectedVersionId(v.voice_profile_version_id)}
                  >
                    v{v.version_no} {v.is_active ? "(active)" : ""}
                  </button>
                ))}
              </div>
              <div className="row" style={{ marginTop: "10px" }}>
                <button className="primary" disabled={busy || !authToken || !vpSelectedVersionId} onClick={onVpActivateVersion}>Activate Selected Version</button>
                <input
                  style={{ maxWidth: "240px" }}
                  value={vpStatusInput}
                  onChange={(e) => setVpStatusInput(e.target.value)}
                  placeholder="approved / rejected / generated"
                />
                <button className="secondary" disabled={busy || !authToken || !vpSelectedVersionId} onClick={onVpUpdateStatus}>Update Status</button>
              </div>
              {vpVersionDetail ? (
                <>
                  <h3 style={{ marginTop: "14px" }}>Version Detail</h3>
                  <pre className="content">{JSON.stringify(vpVersionDetail, null, 2)}</pre>
                </>
              ) : null}
            </div>
          ) : null}
        </>
      )}

      {isAuthenticated && page === "editorial" && (
        <div className="card">
          <h2>Editorial Workspace</h2>
          <div className="grid two">
            <div>
              <label>Select Content Version</label>
              <select value={selectedVersionNumber || ""} onChange={(e) => applySelection(e.target.value)}>
                <option value="" disabled>Select version</option>
                {versions.map((v) => (
                  <option key={v.version_number} value={v.version_number}>
                    {`${getVersionLabel(v)} (v${v.version_number})`}
                  </option>
                ))}
              </select>
            </div>
            <div className="note row" style={{ gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
              <span>Selected kind: <strong>{selectedVersion?.version_kind || "-"}</strong></span>
              <span>Variant label: <strong>{selectedVersion?.variant_label || "-"}</strong></span>
              <span>Stage: <strong>{selectedVersion?.version_stage || "-"}</strong></span>
            </div>
          </div>

          {selectedVersion && (
            <>
              <div className={`split editorial-split ${editorMode !== "none" ? "editorial-split-inline" : ""}`}>
                <div>
                  <h3>Content</h3>
                  {editorMode === "inline" ? (
                    <>
                      <textarea
                        ref={editorialInlineTextareaRef}
                        className="editorial-edit-textarea"
                        value={workingContent}
                        onChange={(e) => {
                          setWorkingContent(e.target.value);
                          autoResizeTextarea(e.target);
                        }}
                      />
                      <div className="row" style={{ marginTop: "8px" }}>
                        <button className="secondary" disabled={busy} onClick={onCancelEditorialEdit}>Cancel</button>
                        <button className="secondary" disabled={busy} onClick={onSaveInline}>Save</button>
                        <button className="primary" disabled={busy} onClick={onFinalizeFromInline}>Finalize Content</button>
                      </div>
                    </>
                  ) : (
                    <>
                      <pre className="content editorial-content-block">{selectedVersion.content || ""}</pre>
                      {editorMode === "none" ? (
                        <div className="row" style={{ marginTop: "8px" }}>
                          <button
                            className="secondary"
                            disabled={busy}
                            onClick={() => {
                              setWorkingContent(selectedVersion.content || "");
                              setEditorMode("inline");
                            }}
                          >
                            Edit Inline
                          </button>
                          <button
                            className="secondary"
                            disabled={busy}
                            onClick={() => {
                              setFeedbackPreviewContent("");
                              setEditorMode("iterate");
                            }}
                          >
                            Iterate
                          </button>
                          <button className="primary" disabled={busy} onClick={onFinalizeSelected}>
                            Finalize Selected
                          </button>
                        </div>
                      ) : null}

                      {editorMode === "iterate" && (
                        <>
                          <h3 style={{ marginTop: "16px" }}>Feedback Editor</h3>
                          <textarea
                            ref={editorialFeedbackTextareaRef}
                            className="editorial-edit-textarea"
                            value={feedbackText}
                            onChange={(e) => {
                              setFeedbackText(e.target.value);
                              autoResizeTextarea(e.target);
                            }}
                          />
                          <div className="row" style={{ marginTop: "8px" }}>
                            <button className="secondary" disabled={busy || isPreviewing} onClick={onCancelEditorialEdit}>Cancel</button>
                            <button className="secondary" disabled={busy} onClick={onFeedbackPreview}>Preview</button>
                            {isPreviewing ? (
                              <div className="row" aria-live="polite">
                                <div className="spinner spinner-inline" />
                                <span className="note">Generating preview...</span>
                              </div>
                            ) : null}
                          </div>
                          {feedbackPreviewContent ? (
                            <>
                              <h3 style={{ marginTop: "16px" }}>Preview Content</h3>
                              <pre className="content editorial-content-block">{feedbackPreviewContent}</pre>
                              <div className="row" style={{ marginTop: "8px" }}>
                                <button className="secondary" disabled={busy} onClick={onSavePreview}>Save</button>
                                <button className="primary" disabled={busy} onClick={onFinalizeFromPreview}>Finalize Content</button>
                              </div>
                            </>
                          ) : null}
                        </>
                      )}
                    </>
                  )}
                </div>

                {editorMode === "none" ? (
                <div>
                  <h3>Keywords</h3>
                  <div className="row">
                    {(selectedVersion.keywords || []).map((kw) => (
                      <span key={kw} className="tag">
                        {kw}
                        <button onClick={() => onPatchKeywords((selectedVersion.keywords || []).filter((x) => x !== kw))}>x</button>
                      </span>
                    ))}
                  </div>
                  <div className="row" style={{ marginTop: "8px" }}>
                    <input
                      value={keywordsInput}
                      onChange={(e) => setKeywordsInput(e.target.value)}
                      placeholder="Add keyword"
                    />
                    <button
                      className="secondary"
                      disabled={busy || !keywordsInput.trim()}
                      onClick={() => onPatchKeywords([...(selectedVersion.keywords || []), keywordsInput.trim()])}
                    >
                      Add
                    </button>
                  </div>
                </div>
                ) : null}
              </div>
            </>
          )}
        </div>
      )}

      {isAuthenticated && page === "artifacts" && (
        <div className="card">
          <h2>Artifact Generator</h2>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
            <div className="row">
              <button
                className={artifactsViewMode === "stored" ? "primary" : "secondary"}
                disabled={busy || isCheckingStoredArtifacts || !hasStoredArtifactsForProject}
                onClick={onViewStoredArtifacts}
              >
                {isStoredArtifactsLoading ? "Loading Artifacts..." : "View Artifacts"}
              </button>
              <button
                className={artifactsViewMode === "generate" || artifactsViewMode === "" ? "primary" : "secondary"}
                disabled={busy}
                onClick={() => setArtifactsViewMode("generate")}
              >
                Generate Artifacts
              </button>
            </div>
            {artifactsViewMode === "stored" ? (
              <div style={{ minWidth: "320px", maxWidth: "420px", flex: "1 1 360px" }}>
                <label>Select Stored Format</label>
                <select
                  value={selectedStoredFormat}
                  onChange={(e) => {
                    setSelectedStoredFormat(e.target.value);
                    setSelectedStoredArtifactTab(0);
                  }}
                >
                  <option value="" disabled>Select format</option>
                  {storedFormats.map((fmt) => (
                    <option key={fmt} value={fmt}>{fmt}</option>
                  ))}
                </select>
              </div>
            ) : <div />}
          </div>
          {artifactsViewMode === "" ? (
            <p className="note">Choose `Generate Artifacts` or `View Artifacts` to load a view.</p>
          ) : null}
          {artifactsViewMode === "generate" ? (
            <>
              <div className="row" style={{ marginBottom: "10px" }}>
                <button
                  type="button"
                  className={artifactGenerateStep === "formats" ? "primary" : "secondary"}
                  disabled={busy}
                  onClick={() => setArtifactGenerateStep("formats")}
                >
                  1. Formats
                </button>
                <button
                  type="button"
                  className={artifactGenerateStep === "style" ? "primary" : "secondary"}
                  disabled={busy || !selectedArtifactFormats.length}
                  onClick={() => setArtifactGenerateStep("style")}
                >
                  2. Style
                </button>
              </div>

              {artifactGenerateStep === "formats" ? (
                <>
                  {["text", "image", "gif", "video", "audio"].map((kind) => {
                    const formats = orderArtifactFormats(kind, artifactFormatsByKind[kind] || []);
                    if (!formats.length) return null;
                    const kindUnavailable = kind === "gif" || kind === "video";
                    const selectedCount = formats.filter((fmt) => selectedArtifactFormats.includes(fmt)).length;
                    const allSelected = formats.length > 0 && selectedCount === formats.length;
                    const showBulkToggle = formats.length > 3 && !kindUnavailable;
                    return (
                      <div key={`wizard-kind-${kind}`} style={{ marginBottom: "22px", opacity: kindUnavailable ? 0.45 : 1 }}>
                        <div className="row" style={{ marginBottom: "10px" }}>
                          <strong style={{ textTransform: "capitalize" }}>{kind}</strong>
                          {kindUnavailable ? (
                            <span className="note" style={{ color: "#c0392b", fontStyle: "italic" }}>temporarily unavailable</span>
                          ) : null}
                          {showBulkToggle ? (
                            <button
                              type="button"
                              className="secondary"
                              disabled={busy}
                              onClick={() => toggleArtifactKind(kind)}
                            >
                              {allSelected ? "Unselect All" : "Select All"}
                            </button>
                          ) : null}
                          {!kindUnavailable ? <span className="note">{selectedCount}/{formats.length} selected</span> : null}
                        </div>
                        <div className="artifact-card-grid">
                          {formats.map((fmt) => {
                            const card = artifactFormatMeta(fmt);
                            const isSelected = selectedArtifactFormats.includes(card.key);
                            const exists = storedArtifactFormatsForProject.includes(card.key);
                            return (
                              <button
                                key={card.key}
                                type="button"
                                className={`artifact-select-card ${exists ? "artifact-select-card-existing" : "artifact-select-card-missing"} ${isSelected ? "artifact-select-card-selected" : ""}`}
                                onClick={() => !kindUnavailable && toggleArtifactFormat(card.key)}
                                disabled={busy || kindUnavailable}
                                title={kindUnavailable ? "Video generation is temporarily unavailable" : undefined}
                                style={kindUnavailable ? { cursor: "not-allowed" } : undefined}
                              >
                                <div className="artifact-select-card-title">{card.title}</div>
                                {card.description ? <div className="artifact-select-card-desc">{card.description}</div> : null}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                  <div className="row" style={{ marginTop: "12px" }}>
                    <span className="note">{selectedArtifactFormats.length} selected</span>
                    {selectedArtifactFormats.length ? (
                      <button
                        type="button"
                        className="primary"
                        disabled={busy}
                        onClick={() => setArtifactGenerateStep("style")}
                      >
                        Next: Style
                      </button>
                    ) : null}
                  </div>
                </>
              ) : null}

              {artifactGenerateStep === "style" ? (
                <>
                  <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginTop: "6px" }}>
                    <div className="note">
                      Selected formats: {artifactSelectedFormatCards.map((x) => x.key).join(", ") || "(none)"}
                    </div>
                  </div>

                  {artifactSelectedKinds.length > 1 ? (
                    <div className="row artifact-kind-tabs" style={{ marginTop: "8px" }}>
                      {artifactSelectedKinds.map((kind) => (
                        <button
                          key={`artifact-style-kind-${kind}`}
                          type="button"
                          className={artifactStyleKindPanel === kind ? "artifact-kind-tab artifact-kind-tab-active" : "artifact-kind-tab"}
                          disabled={busy}
                          onClick={() => setArtifactStyleKindPanel(kind)}
                        >
                          {kind === "text" ? "Text Style" : (kind === "video" || kind === "gif") ? "Video Style" : `${kind[0].toUpperCase()}${kind.slice(1)} Style`}
                        </button>
                      ))}
                    </div>
                  ) : null}

                  {artifactSelectedKinds.includes("text") && artifactStyleKindPanel === "text" ? (
                  <>
                  <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
                    <h3 style={{ marginTop: 0 }}>Style Source</h3>
                    <div className="row">
                      <label className="tag">
                        <input
                          type="radio"
                          name="artifact-style-source"
                          checked={artifactStyleSource === "voice_profile"}
                          onChange={() => setArtifactStyleSource("voice_profile")}
                          style={{ width: "auto", marginRight: "6px" }}
                        />
                        Use saved Voice Profile
                      </label>
                      <label className="tag">
                        <input
                          type="radio"
                          name="artifact-style-source"
                          checked={artifactStyleSource === "manual"}
                          onChange={() => setArtifactStyleSource("manual")}
                          style={{ width: "auto", marginRight: "6px" }}
                        />
                        Enter style manually
                      </label>
                    </div>

                    {artifactStyleSource === "voice_profile" ? (
                      <>
                        <div style={{ marginTop: "10px" }}>
                          <label>voice_profile_id<span className="publish-required-mark"> *</span></label>
                          <select
                            value={artifactStyleVoiceProfileId}
                            onChange={(e) => {
                              setArtifactStyleVoiceProfileId(e.target.value);
                              setArtifactStyleVoiceProfileDetail(null);
                            }}
                          >
                            <option value="">Select voice profile</option>
                            {approvedActiveVoiceProfileOptions.map((opt) => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        </div>
                        {isArtifactStyleVoiceProfileLoading ? (
                          <p className="note" style={{ marginTop: "8px" }}>Loading voice profile preview...</p>
                        ) : null}
                        {artifactSelectedVoiceProfilePreview ? (
                          <div className="artifact-style-preview">
                            <div className="grid two">
                              <div>
                                <label>Voice Style Summary</label>
                                <div className="artifact-preview-box">{artifactSelectedVoiceProfilePreview.core_voice || "not specified"}</div>
                              </div>
                              <div>
                                <label>tone baseline + key traits</label>
                                <pre className="content" style={{ marginTop: "6px" }}>
{JSON.stringify({
  tone_baseline: artifactSelectedVoiceProfilePreview.tone_baseline || {},
  style_summary: artifactSelectedVoiceProfilePreview.style_summary || {},
}, null, 2)}
                                </pre>
                              </div>
                            </div>
                            <div className="grid two" style={{ marginTop: "8px" }}>
                              <div>
                                <label>Do highlights</label>
                                <div className="artifact-preview-box">
                                  {(artifactSelectedVoiceProfilePreview.do_rules || []).slice(0, 6).map((x, i) => <div key={`do-${i}`}>- {x}</div>)}
                                </div>
                              </div>
                              <div>
                                <label>Don't highlights</label>
                                <div className="artifact-preview-box">
                                  {(artifactSelectedVoiceProfilePreview.dont_rules || []).slice(0, 6).map((x, i) => <div key={`dont-${i}`}>- {x}</div>)}
                                </div>
                              </div>
                            </div>
                          </div>
                        ) : null}
                      </>
                    ) : (
                      <div style={{ marginTop: "10px" }}>
                        <label>Voice Style<span className="publish-required-mark"> *</span></label>
                        <textarea
                          value={artifactManualCoreVoice}
                          onChange={(e) => setArtifactManualCoreVoice(e.target.value)}
                          placeholder="How should this sound? e.g., crisp, insightful, slightly witty, no fluff."
                        />
                        <p className="note" style={{ marginTop: "6px" }}>Fast path: only Voice Style + tone nuances required.</p>
                      </div>
                    )}
                  </div>

                  <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
                    <h3 style={{ marginTop: 0 }}>Tone Nuances</h3>
                    <p className="note" style={{ marginTop: "4px" }}>Base tone from project: <strong>{projectToneBase}</strong></p>
                    <div className="grid two">
                      {[
                        ["directness", "Directness", "soft", "direct"],
                        ["warmth", "Warmth", "neutral", "warm"],
                        ["energy", "Energy", "calm", "high-energy"],
                        ["authority", "Authority", "exploratory", "decisive"],
                      ].map(([key, label, left, right]) => (
                        <div key={key}>
                          <label>{label}</label>
                          <input
                            type="range"
                            min="0"
                            max="4"
                            step="1"
                            value={Number(artifactToneNuance[key] ?? 2)}
                            onChange={(e) => updateArtifactToneNuance(key, Number(e.target.value))}
                          />
                          <div className="row note" style={{ justifyContent: "space-between" }}>
                            <span>{left} ↔ {right}</span>
                            <span>{artifactToneNuance[key] ?? 2}/4</span>
                          </div>
                        </div>
                      ))}
                      {projectToneBase === "analytical" ? (
                        <>
                          <div>
                            <label>Rigor</label>
                            <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.rigor ?? 3)} onChange={(e) => updateArtifactToneNuance("rigor", Number(e.target.value))} />
                            <div className="row note" style={{ justifyContent: "space-between" }}><span>intuitive ↔ evidence-led</span><span>{artifactToneNuance.rigor ?? 3}/4</span></div>
                          </div>
                          <div>
                            <label>Abstraction level</label>
                            <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.abstraction ?? 2)} onChange={(e) => updateArtifactToneNuance("abstraction", Number(e.target.value))} />
                            <div className="row note" style={{ justifyContent: "space-between" }}><span>tactical ↔ strategic</span><span>{artifactToneNuance.abstraction ?? 2}/4</span></div>
                          </div>
                          <div>
                            <label>Framework mode</label>
                            <select value={artifactFrameworkMode} onChange={(e) => setArtifactFrameworkMode(e.target.value)}>
                              <option value="none">none</option>
                              <option value="light">light</option>
                              <option value="strong">strong</option>
                            </select>
                          </div>
                        </>
                      ) : null}
                      {projectToneBase === "professional" ? (
                        <>
                          <div>
                            <label>Formality</label>
                            <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.formality ?? 3)} onChange={(e) => updateArtifactToneNuance("formality", Number(e.target.value))} />
                            <div className="row note" style={{ justifyContent: "space-between" }}><span>relaxed ↔ formal</span><span>{artifactToneNuance.formality ?? 3}/4</span></div>
                          </div>
                          <div>
                            <label>Diplomacy</label>
                            <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.diplomacy ?? 3)} onChange={(e) => updateArtifactToneNuance("diplomacy", Number(e.target.value))} />
                            <div className="row note" style={{ justifyContent: "space-between" }}><span>blunt ↔ tactful</span><span>{artifactToneNuance.diplomacy ?? 3}/4</span></div>
                          </div>
                        </>
                      ) : null}
                      {projectToneBase === "conversational" ? (
                        <>
                          <div>
                            <label>Humor</label>
                            <input
                              type="range"
                              min="0"
                              max="2"
                              step="1"
                              value={humorLabelToSlider(artifactToneNuance.humor || "light")}
                              onChange={(e) => updateArtifactToneNuance("humor", humorSliderToLabel(Number(e.target.value)))}
                            />
                            <div className="row note" style={{ justifyContent: "space-between" }}>
                              <span>none ↔ playful</span>
                              <span>{String(artifactToneNuance.humor || "light")}</span>
                            </div>
                          </div>
                          <div>
                            <label>Story-ness</label>
                            <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.storyness ?? 2)} onChange={(e) => updateArtifactToneNuance("storyness", Number(e.target.value))} />
                            <div className="row note" style={{ justifyContent: "space-between" }}><span>straightforward ↔ story-led</span><span>{artifactToneNuance.storyness ?? 2}/4</span></div>
                          </div>
                        </>
                      ) : null}
                    </div>
                  </div>

                  {artifactSelectedAdvancedFormatCards.length ? (
                    <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
                      <h3 style={{ marginTop: 0 }}>Format-specific Advanced Settings (optional)</h3>
                      {artifactSelectedAdvancedFormatCards.map((card) => {
                        const adv = artifactFormatAdvanced?.[card.key] || {};
                        const open = !!artifactAdvancedOpen?.[card.key];
                        return (
                          <div key={`adv-${card.key}`} className="artifact-advanced-block">
                            <button
                              type="button"
                              className={`artifact-advanced-toggle ${open ? "artifact-advanced-toggle-open" : ""}`}
                              onClick={() => toggleArtifactAdvancedDrawer(card.key)}
                            >
                              <span>
                                <strong>{card.key}</strong>
                                <span className="note" style={{ marginLeft: "8px" }}>{card.description}</span>
                              </span>
                              <span className="note">{open ? "Collapse" : "Expand"}</span>
                            </button>
                            {open ? (
                              <div className="grid two" style={{ marginTop: "8px" }}>
                                {card.key === "caption" ? (
                                  <>
                                    <div><label>length</label><select value={adv.length || "short"} onChange={(e) => updateArtifactAdvanced("caption", "length", e.target.value)}><option value="short">short</option><option value="medium">medium</option></select></div>
                                    <div><label>emoji_density</label><select value={adv.emoji_density || "light"} onChange={(e) => updateArtifactAdvanced("caption", "emoji_density", e.target.value)}><option value="none">none</option><option value="light">light</option><option value="medium">medium</option><option value="high">high</option></select></div>
                                    <div><label>structure_hint</label><select value={adv.structure_hint || "plain"} onChange={(e) => updateArtifactAdvanced("caption", "structure_hint", e.target.value)}><option value="plain">plain</option><option value="bullet-ish">bullet-ish</option><option value="mini-story">mini-story</option></select></div>
                                  </>
                                ) : null}
                                {card.key === "post" ? (
                                  <>
                                    <div><label>length</label><select value={adv.length || "medium"} onChange={(e) => updateArtifactAdvanced("post", "length", e.target.value)}><option value="short">short</option><option value="medium">medium</option><option value="long">long</option></select></div>
                                    <div><label>structure_hint</label><select value={adv.structure_hint || "framework-led"} onChange={(e) => updateArtifactAdvanced("post", "structure_hint", e.target.value)}><option value="framework-led">framework-led</option><option value="story-led">story-led</option><option value="list-led">list-led</option></select></div>
                                    <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("post", "cta_strength", e.target.value)}><option value="soft">soft</option><option value="medium">medium</option><option value="strong">strong</option></select></div>
                                  </>
                                ) : null}
                                {card.key === "newsletter" ? (
                                  <>
                                    <div><label>sections</label><select value={adv.sections || 4} onChange={(e) => updateArtifactAdvanced("newsletter", "sections", Number(e.target.value))}><option value={3}>3</option><option value={4}>4</option><option value={5}>5</option></select></div>
                                    <div><label>takeaway_bullets</label><input type="number" min="3" max="6" value={adv.takeaway_bullets || 4} onChange={(e) => updateArtifactAdvanced("newsletter", "takeaway_bullets", Number(e.target.value))} /></div>
                                    <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("newsletter", "cta_strength", e.target.value)}><option value="soft">soft</option><option value="medium">medium</option><option value="strong">strong</option></select></div>
                                  </>
                                ) : null}
                                {card.key === "blog" ? (
                                  <>
                                    <div><label>seo_intent</label><select value={adv.seo_intent || "informational"} onChange={(e) => updateArtifactAdvanced("blog", "seo_intent", e.target.value)}><option value="informational">informational</option><option value="how-to">how-to</option><option value="comparison">comparison</option></select></div>
                                    <div><label>faq_count</label><input type="number" min="0" max="5" value={adv.faq_count ?? 3} onChange={(e) => updateArtifactAdvanced("blog", "faq_count", Number(e.target.value))} /></div>
                                    <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("blog", "cta_strength", e.target.value)}><option value="soft">soft</option><option value="medium">medium</option><option value="strong">strong</option></select></div>
                                  </>
                                ) : null}
                                {card.key === "script_short" ? (
                                  <>
                                    <div><label>target_duration_sec</label><select value={adv.target_duration_sec || 30} onChange={(e) => updateArtifactAdvanced("script_short", "target_duration_sec", Number(e.target.value))}><option value={15}>15</option><option value={30}>30</option><option value={45}>45</option><option value={60}>60</option></select></div>
                                    <div><label>pacing</label><select value={adv.pacing || "normal"} onChange={(e) => updateArtifactAdvanced("script_short", "pacing", e.target.value)}><option value="slow">slow</option><option value="normal">normal</option><option value="fast">fast</option></select></div>
                                    <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("script_short", "cta_strength", e.target.value)}><option value="soft">soft</option><option value="medium">medium</option><option value="strong">strong</option></select></div>
                                  </>
                                ) : null}
                                {card.key === "cta_variants" ? (
                                  <>
                                    <div><label>variant_count</label><input type="number" min="7" max="11" value={adv.variant_count || 7} onChange={(e) => updateArtifactAdvanced("cta_variants", "variant_count", Number(e.target.value))} /></div>
                                    <div style={{ gridColumn: "1 / -1" }}>
                                      <label>angles</label>
                                      <div className="row" style={{ marginTop: "6px" }}>
                                        {["urgency", "curiosity", "benefit", "social-proof", "low-friction", "question"].map((angle) => (
                                          <label key={angle} className="tag">
                                            <input
                                              type="checkbox"
                                              checked={Array.isArray(adv.angles) && adv.angles.includes(angle)}
                                              onChange={() => toggleArtifactAdvancedAngle(angle)}
                                              style={{ width: "auto", marginRight: "6px" }}
                                            />
                                            {angle}
                                          </label>
                                        ))}
                                      </div>
                                    </div>
                                  </>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                  </>
                  ) : null}

                  {artifactSelectedKinds.includes("image") && artifactStyleKindPanel === "image" ? (
                    <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
                      <h3 style={{ marginTop: 0 }}>Image Style</h3>
                      <p className="note" style={{ marginTop: "4px" }}>
                        Selected image formats: {artifactSelectedImageFormatCards.map((x) => x.key).join(", ") || "(none)"}
                      </p>

                      <div className="artifact-style-subsection">
                        <h4 className="artifact-style-subheading">Creative Direction</h4>
                        <div className="grid two">
                          <div>
                            <label>Theme<span className="publish-required-mark"> *</span></label>
                            <input
                              className="suggestive-placeholder"
                              value={artifactImageStyle.theme || ""}
                              onChange={(e) => updateArtifactImageStyle("theme", e.target.value)}
                              placeholder='e.g. "luxury chocolate", "minimal fintech", "kids comic"'
                            />
                          </div>
                          <div style={{ gridColumn: "1 / -1" }}>
                            <label>Subject / core prompt<span className="publish-required-mark"> *</span></label>
                            <textarea
                              className="suggestive-placeholder"
                              value={artifactImageStyle.subject_prompt || ""}
                              onChange={(e) => updateArtifactImageStyle("subject_prompt", e.target.value)}
                              placeholder="What should be in the image (who/what + setting + action)."
                            />
                          </div>
                          <div style={{ gridColumn: "1 / -1" }}>
                            <label>Avoid / don't include</label>
                            <div className="row artifact-inline-input">
                              <input
                                value={artifactImageAvoidInput}
                                onChange={(e) => setArtifactImageAvoidInput(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    e.preventDefault();
                                    addArtifactImageAvoidTag();
                                  }
                                }}
                                placeholder="Add tag (e.g. watermark, clutter, brand logos)"
                              />
                              <button type="button" className="secondary" onClick={addArtifactImageAvoidTag} disabled={busy}>
                                Add
                              </button>
                            </div>
                            <div className="row" style={{ marginTop: "6px" }}>
                              {(artifactImageStyle.avoid || []).map((tag) => (
                                <span key={tag} className="tag">
                                  {tag}
                                  <button type="button" onClick={() => removeArtifactImageAvoidTag(tag)} aria-label={`Remove ${tag}`}>
                                    x
                                  </button>
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="artifact-style-subsection">
                        <h4 className="artifact-style-subheading">Visual Display</h4>
                        <div className="grid two">
                          <div>
                            <label>Medium</label>
                            <select value={artifactImageStyle.medium || "illustration"} onChange={(e) => updateArtifactImageStyle("medium", e.target.value)}>
                              {["photo", "illustration", "3d_render", "comic", "watercolor", "oil_paint", "vector_flat", "pixel_art"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Texture</label>
                            <select value={artifactImageStyle.texture || "clean"} onChange={(e) => updateArtifactImageStyle("texture", e.target.value)}>
                              {["clean", "film_grain", "halftone", "paper", "canvas", "noise"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Lighting</label>
                            <select value={artifactImageStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactImageStyle("lighting", e.target.value)}>
                              {["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Palette mode</label>
                            <select value={artifactImageStyle.palette_mode || "muted"} onChange={(e) => updateArtifactImageStyle("palette_mode", e.target.value)}>
                              {["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Output fidelity</label>
                            <div className="row">
                              <button
                                type="button"
                                className={(artifactImageStyle.output_fidelity || "standard") === "standard" ? "primary" : "secondary"}
                                onClick={() => updateArtifactImageStyle("output_fidelity", "standard")}
                              >
                                Standard
                              </button>
                              <button
                                type="button"
                                className={(artifactImageStyle.output_fidelity || "standard") === "hd" ? "primary" : "secondary"}
                                onClick={() => updateArtifactImageStyle("output_fidelity", "hd")}
                              >
                                HD
                              </button>
                            </div>
                          </div>
                          {(artifactImageStyle.palette_mode || "") === "brand" ? (
                            <div style={{ gridColumn: "1 / -1" }}>
                              <label>Brand colors</label>
                              <div className="grid two">
                                {["primary", "secondary", "accent", "background"].map((slot) => (
                                  <div key={slot}>
                                    <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                                    <div className="row">
                                      <input
                                        type="color"
                                        value={artifactImageStyle?.brand_colors?.[slot] || "#000000"}
                                        onChange={(e) => updateArtifactImageBrandColor(slot, e.target.value)}
                                        style={{ width: "48px", padding: "2px", height: "38px" }}
                                      />
                                      <input
                                        value={artifactImageStyle?.brand_colors?.[slot] || ""}
                                        onChange={(e) => updateArtifactImageBrandColor(slot, e.target.value)}
                                        placeholder="#000000"
                                      />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : null}
                        </div>
                      </div>

                      <div className="artifact-style-subsection">
                        <h4 className="artifact-style-subheading">Composition</h4>
                        <div className="grid two">
                          <div>
                            <label>Mood</label>
                            <select value={artifactImageStyle.mood || "premium"} onChange={(e) => updateArtifactImageStyle("mood", e.target.value)}>
                              {["playful", "serious", "premium", "cozy", "dramatic", "energetic"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Focus / negative space</label>
                            <select
                              value={artifactImageStyle.focus_negative_space || "subject_centered"}
                              onChange={(e) => updateArtifactImageStyle("focus_negative_space", e.target.value)}
                            >
                              {["subject_centered", "rule_of_thirds", "negative_space_left", "negative_space_right"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {((artifactSelectedKinds.includes("video") && artifactStyleKindPanel === "video") ||
                    (artifactSelectedKinds.includes("gif") && artifactStyleKindPanel === "gif")) ? (
                    <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
                      <h3 style={{ marginTop: 0 }}>Video Style</h3>
                      <p className="note" style={{ marginTop: "4px" }}>
                        Selected video formats: {artifactSelectedVideoFormatCards.map((x) => x.key).join(", ") || "(none)"}
                      </p>

                      <div className="artifact-style-subsection">
                        <h4 className="artifact-style-subheading">Creative Direction</h4>
                        <div className="grid two">
                          <div>
                            <label>Theme<span className="publish-required-mark"> *</span></label>
                            <input
                              className="suggestive-placeholder"
                              value={artifactVideoStyle.theme || ""}
                              onChange={(e) => updateArtifactVideoStyle("theme", e.target.value)}
                              placeholder='e.g. "futuristic product launch", "cozy cooking loop"'
                            />
                          </div>
                          <div style={{ gridColumn: "1 / -1" }}>
                            <label>Subject / core prompt<span className="publish-required-mark"> *</span></label>
                            <textarea
                              className="suggestive-placeholder"
                              value={artifactVideoStyle.subject_prompt || ""}
                              onChange={(e) => updateArtifactVideoStyle("subject_prompt", e.target.value)}
                              placeholder="What should be in the video (who/what + setting + action)."
                            />
                          </div>
                          <div style={{ gridColumn: "1 / -1" }}>
                            <label>Avoid / don't include</label>
                            <div className="row artifact-inline-input">
                              <input
                                value={artifactVideoAvoidInput}
                                onChange={(e) => setArtifactVideoAvoidInput(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    e.preventDefault();
                                    addArtifactVideoAvoidTag();
                                  }
                                }}
                                placeholder="Add tag (e.g. watermarks, logos, real people)"
                              />
                              <button type="button" className="secondary" onClick={addArtifactVideoAvoidTag} disabled={busy}>
                                Add
                              </button>
                            </div>
                            <div className="row" style={{ marginTop: "6px" }}>
                              {(artifactVideoStyle.avoid || []).map((tag) => (
                                <span key={`video-avoid-${tag}`} className="tag">
                                  {tag}
                                  <button type="button" onClick={() => removeArtifactVideoAvoidTag(tag)} aria-label={`Remove ${tag}`}>
                                    x
                                  </button>
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="artifact-style-subsection">
                        <h4 className="artifact-style-subheading">Visual Display</h4>
                        <div className="grid two">
                          <div>
                            <label>Mood</label>
                            <select value={artifactVideoStyle.mood || "energetic"} onChange={(e) => updateArtifactVideoStyle("mood", e.target.value)}>
                              {["playful", "serious", "premium", "cozy", "dramatic", "energetic", "inspiring", "suspenseful", "mysterious", "whimsical", "futuristic", "nostalgic"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Lighting</label>
                            <select value={artifactVideoStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactVideoStyle("lighting", e.target.value)}>
                              {["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Palette mode</label>
                            <select value={artifactVideoStyle.palette_mode || "muted"} onChange={(e) => updateArtifactVideoStyle("palette_mode", e.target.value)}>
                              {["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Output fidelity</label>
                            <select value={artifactVideoStyle.output_fidelity || "standard"} onChange={(e) => updateArtifactVideoStyle("output_fidelity", e.target.value)}>
                              <option value="standard">standard</option>
                              <option value="pro">pro</option>
                            </select>
                          </div>
                          {(artifactVideoStyle.palette_mode || "") === "brand" ? (
                            <div style={{ gridColumn: "1 / -1" }}>
                              <label>Brand colors</label>
                              <div className="grid two">
                                {["primary", "secondary", "accent", "background"].map((slot) => (
                                  <div key={`video-color-${slot}`}>
                                    <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                                    <div className="row">
                                      <input
                                        type="color"
                                        value={artifactVideoStyle?.brand_colors?.[slot] || "#000000"}
                                        onChange={(e) => updateArtifactVideoBrandColor(slot, e.target.value)}
                                        style={{ width: "48px", padding: "2px", height: "38px" }}
                                      />
                                      <input
                                        value={artifactVideoStyle?.brand_colors?.[slot] || ""}
                                        onChange={(e) => updateArtifactVideoBrandColor(slot, e.target.value)}
                                        placeholder="#000000"
                                      />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : null}
                        </div>
                      </div>

                      <div className="artifact-style-subsection">
                        <h4 className="artifact-style-subheading">Composition</h4>
                        <p className="note" style={{ marginTop: "4px" }}>
                          Standard composition controls (pacing, motion intensity, safe zones) are applied automatically per format. Override below as needed.
                        </p>
                        <div className="grid two" style={{ marginTop: "10px" }}>
                          <div>
                            <label>Camera motion</label>
                            <select value={artifactVideoStyle.camera_motion || ""} onChange={(e) => updateArtifactVideoStyle("camera_motion", e.target.value)}>
                              <option value="">Auto</option>
                              {["slow_dolly_in", "orbital_drift", "tracking_follow", "static_locked", "handheld_documentary", "push_pull_oscillate"].map((v) => (
                                <option key={v} value={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label>Energy level</label>
                            <div className="row">
                              {["low", "medium", "high"].map((level) => (
                                <button
                                  key={level}
                                  type="button"
                                  className={(artifactVideoStyle.energy_level || "medium") === level ? "primary" : "secondary"}
                                  onClick={() => updateArtifactVideoStyle("energy_level", level)}
                                >
                                  {level.charAt(0).toUpperCase() + level.slice(1)}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : null}

                  <div className="row" style={{ marginTop: "12px" }}>
                    <button className="primary" disabled={busy || !canGenerateArtifactsNow} onClick={onGenerateArtifacts}>
                      {isArtifactGenerating ? "Generating Artifacts..." : "Generate Selected Artifacts"}
                    </button>
                  </div>
                </>
              ) : null}
            </>
          ) : null}
          {isCheckingStoredArtifacts ? (
            <p className="note" style={{ marginTop: "8px" }}>Checking stored artifacts for this project...</p>
          ) : null}
          {artifactsViewMode === "generate" && generatedArtifacts.length > 0 ? (
            <>
              <h3 style={{ marginTop: "16px" }}>Generated Artifacts</h3>
              <div className="row" style={{ marginBottom: "8px" }}>
                {generatedArtifacts.map((artifact, idx) => (
                  <button
                    key={`${artifact.artifact_id || artifact.format}-${idx}`}
                    type="button"
                    className={idx === selectedArtifactTab ? "primary" : "secondary"}
                    onClick={() => setSelectedArtifactTab(idx)}
                  >
                    {artifact.format}
                  </button>
                ))}
              </div>
              {selectedGeneratedArtifact ? (
                <pre className="content">{JSON.stringify(selectedGeneratedArtifact, null, 2)}</pre>
              ) : null}
            </>
          ) : null}
          {artifactsViewMode === "stored" && storedArtifacts.length > 0 ? (
            <>
              <h3 style={{ marginTop: "16px" }}>Stored Artifacts</h3>
              {filteredStoredArtifacts.length > 0 ? (
                <>
                  <div className="row" style={{ marginTop: "8px", marginBottom: "8px" }}>
                    {filteredStoredArtifacts.map((artifact, idx) => (
                      <div
                        key={`${artifact.artifact_id || selectedStoredFormat}-${idx}`}
                        className={`artifact-title-chip ${idx === selectedStoredArtifactTab ? "artifact-title-chip-active" : ""}`}
                      >
                        {editingArtifactTitleId === artifact?.artifact_id ? (
                          <div className="row" style={{ gap: "6px", flexWrap: "nowrap" }}>
                            <input
                              value={editingArtifactTitleValue}
                              onChange={(e) => setEditingArtifactTitleValue(e.target.value)}
                              onBlur={() => saveArtifactTitle(artifact)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.preventDefault();
                                  saveArtifactTitle(artifact);
                                } else if (e.key === "Escape") {
                                  e.preventDefault();
                                  cancelEditingArtifactTitle();
                                }
                              }}
                              placeholder={`${selectedStoredFormat} #${idx + 1}`}
                              style={{ minWidth: "220px", width: "auto" }}
                              autoFocus
                            />
                          </div>
                        ) : (
                          <button
                            type="button"
                            className={idx === selectedStoredArtifactTab ? "primary" : "secondary"}
                            onClick={() => {
                              if (idx === selectedStoredArtifactTab) {
                                startEditingArtifactTitle(artifact);
                              } else {
                                setSelectedStoredArtifactTab(idx);
                              }
                            }}
                            aria-label={`Select or rename ${artifact.title || `${selectedStoredFormat} #${idx + 1}`}`}
                          >
                            {artifact.title || `${selectedStoredFormat} #${idx + 1}`}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  {selectedStoredArtifact ? (
                    <>
                      {artifactEditMode === "inline" ? (
                        <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
                          <LabelWithTooltip
                            text="Edit Inline"
                            tooltip="Directly edit text content. Save will update DB and overwrite the same Azure blob path when available."
                          />
                          <textarea
                            ref={artifactInlineTextareaRef}
                            className="artifact-edit-textarea"
                            value={artifactInlineText}
                            onChange={(e) => {
                              setArtifactInlineText(e.target.value);
                              autoResizeTextarea(e.target);
                            }}
                            placeholder="Edit artifact content..."
                          />
                          <div className="row" style={{ marginTop: "8px" }}>
                            <button
                              type="button"
                              className="primary"
                              disabled={busy || isArtifactEditing}
                              onClick={onSaveInlineArtifactEdit}
                            >
                              {isArtifactEditing ? "Saving..." : "Save Inline Edit"}
                            </button>
                            <button type="button" className="secondary" disabled={busy || isArtifactEditing} onClick={resetArtifactEditPanel}>
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : null}

                      {artifactEditMode === "iterate" ? (
                        <>
                          <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
                            <LabelWithTooltip
                              text="Edit Instruction"
                              tooltip="Describe exactly how to modify this artifact."
                            />
                            <textarea
                              ref={artifactIterateInstructionTextareaRef}
                              className="artifact-edit-textarea"
                              value={artifactIterateInstruction}
                              onChange={(e) => {
                                setArtifactIterateInstruction(e.target.value);
                                autoResizeTextarea(e.target);
                              }}
                              placeholder="Describe how to modify this artifact..."
                            />
                          </div>

                          {String(selectedStoredArtifact?.kind || "").trim() === "text" ? (
                            <>
                              <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
                                <h3 style={{ marginTop: 0 }}>Style Source</h3>
                                <div className="row">
                                  <label className="tag">
                                    <input
                                      type="radio"
                                      name="artifact-iterate-style-source"
                                      checked={artifactIterateStyleSource === "voice_profile"}
                                      onChange={() => setArtifactIterateStyleSource("voice_profile")}
                                      style={{ width: "auto", marginRight: "6px" }}
                                    />
                                    Use saved Voice Profile
                                  </label>
                                  <label className="tag">
                                    <input
                                      type="radio"
                                      name="artifact-iterate-style-source"
                                      checked={artifactIterateStyleSource === "manual"}
                                      onChange={() => setArtifactIterateStyleSource("manual")}
                                      style={{ width: "auto", marginRight: "6px" }}
                                    />
                                    Enter style manually
                                  </label>
                                </div>
                                {artifactIterateStyleSource === "voice_profile" ? (
                                  <div style={{ marginTop: "8px" }}>
                                    <label>voice_profile_id</label>
                                    <select value={artifactIterateVoiceProfileId} onChange={(e) => setArtifactIterateVoiceProfileId(e.target.value)}>
                                      <option value="">Select voice profile</option>
                                      {approvedActiveVoiceProfileOptions.map((opt) => (
                                        <option key={`iter-vp-${opt.value}`} value={opt.value}>{opt.label}</option>
                                      ))}
                                    </select>
                                  </div>
                                ) : (
                                  <div style={{ marginTop: "8px" }}>
                                    <label>Voice Style</label>
                                    <textarea
                                      ref={artifactIterateVoiceStyleTextareaRef}
                                      className="artifact-edit-textarea"
                                      value={artifactIterateManualCoreVoice}
                                      onChange={(e) => {
                                        setArtifactIterateManualCoreVoice(e.target.value);
                                        autoResizeTextarea(e.target);
                                      }}
                                      placeholder="How should this revised artifact sound?"
                                    />
                                  </div>
                                )}
                              </div>

                              <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
                                <h3 style={{ marginTop: 0 }}>Tone Nuances</h3>
                                <div className="grid two">
                                  {[
                                    ["directness", "Directness", "soft", "direct"],
                                    ["warmth", "Warmth", "neutral", "warm"],
                                    ["energy", "Energy", "calm", "high-energy"],
                                    ["authority", "Authority", "exploratory", "decisive"],
                                  ].map(([key, label, left, right]) => (
                                    <div key={`iter-tone-${key}`}>
                                      <label>{label}</label>
                                      <input
                                        type="range"
                                        min="0"
                                        max="4"
                                        step="1"
                                        value={Number(artifactIterateToneNuance[key] ?? 2)}
                                        onChange={(e) => updateArtifactIterateToneNuance(key, Number(e.target.value))}
                                      />
                                      <div className="row note" style={{ justifyContent: "space-between" }}>
                                        <span>{left} ↔ {right}</span>
                                        <span>{artifactIterateToneNuance[key] ?? 2}/4</span>
                                      </div>
                                    </div>
                                  ))}
                                  {toneBaseFromProjectTone(form.tone_preference) === "analytical" ? (
                                    <>
                                      <div>
                                        <label>Rigor</label>
                                        <input type="range" min="0" max="4" step="1" value={Number(artifactIterateToneNuance.rigor ?? 3)} onChange={(e) => updateArtifactIterateToneNuance("rigor", Number(e.target.value))} />
                                      </div>
                                      <div>
                                        <label>Abstraction</label>
                                        <input type="range" min="0" max="4" step="1" value={Number(artifactIterateToneNuance.abstraction ?? 2)} onChange={(e) => updateArtifactIterateToneNuance("abstraction", Number(e.target.value))} />
                                      </div>
                                      <div>
                                        <label>Framework mode</label>
                                        <select value={artifactIterateFrameworkMode} onChange={(e) => setArtifactIterateFrameworkMode(e.target.value)}>
                                          <option value="none">none</option>
                                          <option value="light">light</option>
                                          <option value="strong">strong</option>
                                        </select>
                                      </div>
                                    </>
                                  ) : null}
                                </div>
                              </div>

                              {Object.prototype.hasOwnProperty.call(FORMAT_ADVANCED_DEFAULTS, String(selectedStoredArtifact?.format || "")) ? (
                                <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
                                  <h3 style={{ marginTop: 0 }}>Format-specific Advanced Settings (optional)</h3>
                                  <div className="grid two">
                                    {String(selectedStoredArtifact?.format || "") === "post" ? (
                                      <>
                                        <div><label>length</label><select value={artifactIterateFormatAdvanced?.post?.length || "medium"} onChange={(e) => updateArtifactIterateAdvanced("post", "length", e.target.value)}><option value="short">short</option><option value="medium">medium</option><option value="long">long</option></select></div>
                                        <div><label>structure_hint</label><select value={artifactIterateFormatAdvanced?.post?.structure_hint || "framework-led"} onChange={(e) => updateArtifactIterateAdvanced("post", "structure_hint", e.target.value)}><option value="framework-led">framework-led</option><option value="story-led">story-led</option><option value="list-led">list-led</option></select></div>
                                        <div><label>cta_strength</label><select value={artifactIterateFormatAdvanced?.post?.cta_strength || "medium"} onChange={(e) => updateArtifactIterateAdvanced("post", "cta_strength", e.target.value)}><option value="soft">soft</option><option value="medium">medium</option><option value="strong">strong</option></select></div>
                                      </>
                                    ) : null}
                                    {String(selectedStoredArtifact?.format || "") === "caption" ? (
                                      <>
                                        <div><label>length</label><select value={artifactIterateFormatAdvanced?.caption?.length || "short"} onChange={(e) => updateArtifactIterateAdvanced("caption", "length", e.target.value)}><option value="short">short</option><option value="medium">medium</option></select></div>
                                        <div><label>emoji_density</label><select value={artifactIterateFormatAdvanced?.caption?.emoji_density || "light"} onChange={(e) => updateArtifactIterateAdvanced("caption", "emoji_density", e.target.value)}><option value="none">none</option><option value="light">light</option><option value="moderate">moderate</option></select></div>
                                      </>
                                    ) : null}
                                    {String(selectedStoredArtifact?.format || "") === "newsletter" ? (
                                      <>
                                        <div><label>sections</label><input type="number" min="3" max="6" value={artifactIterateFormatAdvanced?.newsletter?.sections || 4} onChange={(e) => updateArtifactIterateAdvanced("newsletter", "sections", Number(e.target.value))} /></div>
                                        <div><label>takeaway_bullets</label><input type="number" min="3" max="6" value={artifactIterateFormatAdvanced?.newsletter?.takeaway_bullets || 4} onChange={(e) => updateArtifactIterateAdvanced("newsletter", "takeaway_bullets", Number(e.target.value))} /></div>
                                      </>
                                    ) : null}
                                    {String(selectedStoredArtifact?.format || "") === "blog" ? (
                                      <>
                                        <div><label>seo_intent</label><select value={artifactIterateFormatAdvanced?.blog?.seo_intent || "informational"} onChange={(e) => updateArtifactIterateAdvanced("blog", "seo_intent", e.target.value)}><option value="informational">informational</option><option value="how-to">how-to</option><option value="comparison">comparison</option></select></div>
                                        <div><label>faq_count</label><input type="number" min="0" max="5" value={artifactIterateFormatAdvanced?.blog?.faq_count || 3} onChange={(e) => updateArtifactIterateAdvanced("blog", "faq_count", Number(e.target.value))} /></div>
                                      </>
                                    ) : null}
                                    {String(selectedStoredArtifact?.format || "") === "script_short" ? (
                                      <>
                                        <div><label>target_duration_sec</label><input type="number" min="10" max="120" value={artifactIterateFormatAdvanced?.script_short?.target_duration_sec || 30} onChange={(e) => updateArtifactIterateAdvanced("script_short", "target_duration_sec", Number(e.target.value))} /></div>
                                        <div><label>pacing</label><select value={artifactIterateFormatAdvanced?.script_short?.pacing || "normal"} onChange={(e) => updateArtifactIterateAdvanced("script_short", "pacing", e.target.value)}><option value="slow">slow</option><option value="normal">normal</option><option value="fast">fast</option></select></div>
                                      </>
                                    ) : null}
                                    {String(selectedStoredArtifact?.format || "") === "cta_variants" ? (
                                      <>
                                        <div><label>variant_count</label><input type="number" min="7" max="11" value={artifactIterateFormatAdvanced?.cta_variants?.variant_count || 7} onChange={(e) => updateArtifactIterateAdvanced("cta_variants", "variant_count", Number(e.target.value))} /></div>
                                        <div><label>angles (comma-separated)</label><input value={Array.isArray(artifactIterateFormatAdvanced?.cta_variants?.angles) ? artifactIterateFormatAdvanced.cta_variants.angles.join(", ") : ""} onChange={(e) => updateArtifactIterateAdvanced("cta_variants", "angles", String(e.target.value || "").split(",").map((x) => x.trim()).filter(Boolean))} /></div>
                                      </>
                                    ) : null}
                                  </div>
                                </div>
                              ) : null}
                            </>
                          ) : null}

                          {String(selectedStoredArtifact?.kind || "").trim() === "image" ? (
                            <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
                              <h3 style={{ marginTop: 0 }}>Image Style</h3>
                              <div className="artifact-style-subsection">
                                <h4 className="artifact-style-subheading">Visual Display</h4>
                                <div className="grid two">
                                  <div><label>Medium</label><select value={artifactIterateImageStyle.medium || "illustration"} onChange={(e) => updateArtifactIterateImageStyle("medium", e.target.value)}>{["photo", "illustration", "3d_render", "comic", "watercolor", "oil_paint", "vector_flat", "pixel_art"].map((v) => <option key={`iter-img-med-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Texture</label><select value={artifactIterateImageStyle.texture || "clean"} onChange={(e) => updateArtifactIterateImageStyle("texture", e.target.value)}>{["clean", "film_grain", "halftone", "paper", "canvas", "noise"].map((v) => <option key={`iter-img-tex-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Lighting</label><select value={artifactIterateImageStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactIterateImageStyle("lighting", e.target.value)}>{["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => <option key={`iter-img-light-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Palette mode</label><select value={artifactIterateImageStyle.palette_mode || "muted"} onChange={(e) => updateArtifactIterateImageStyle("palette_mode", e.target.value)}>{["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => <option key={`iter-img-pal-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Output fidelity</label><select value={artifactIterateImageStyle.output_fidelity || "standard"} onChange={(e) => updateArtifactIterateImageStyle("output_fidelity", e.target.value)}><option value="standard">standard</option><option value="hd">hd</option></select></div>
                                  {(artifactIterateImageStyle.palette_mode || "") === "brand" ? (
                                    <div style={{ gridColumn: "1 / -1" }}>
                                      <label>Brand colors</label>
                                      <div className="grid two">
                                        {["primary", "secondary", "accent", "background"].map((slot) => (
                                          <div key={`iter-img-color-${slot}`}>
                                            <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                                            <div className="row">
                                              <input type="color" value={artifactIterateImageStyle?.brand_colors?.[slot] || "#000000"} onChange={(e) => updateArtifactIterateImageBrandColor(slot, e.target.value)} style={{ width: "48px", padding: "2px", height: "38px" }} />
                                              <input value={artifactIterateImageStyle?.brand_colors?.[slot] || ""} onChange={(e) => updateArtifactIterateImageBrandColor(slot, e.target.value)} placeholder="#000000" />
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ) : null}
                                </div>
                              </div>
                              <div className="artifact-style-subsection">
                                <h4 className="artifact-style-subheading">Composition</h4>
                                <div className="grid two">
                                  <div><label>Mood</label><select value={artifactIterateImageStyle.mood || "premium"} onChange={(e) => updateArtifactIterateImageStyle("mood", e.target.value)}>{["playful", "serious", "premium", "cozy", "dramatic", "energetic"].map((v) => <option key={`iter-img-mood-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Focus / negative space</label><select value={artifactIterateImageStyle.focus_negative_space || "subject_centered"} onChange={(e) => updateArtifactIterateImageStyle("focus_negative_space", e.target.value)}>{["subject_centered", "rule_of_thirds", "negative_space_left", "negative_space_right"].map((v) => <option key={`iter-img-focus-${v}`} value={v}>{v}</option>)}</select></div>
                                </div>
                              </div>
                            </div>
                          ) : null}

                          {(String(selectedStoredArtifact?.kind || "").trim() === "video" || String(selectedStoredArtifact?.kind || "").trim() === "gif") ? (
                            <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
                              <h3 style={{ marginTop: 0 }}>Video Style</h3>
                              <div className="artifact-style-subsection">
                                <h4 className="artifact-style-subheading">Visual Display</h4>
                                <div className="grid two">
                                  <div><label>Mood</label><select value={artifactIterateVideoStyle.mood || "energetic"} onChange={(e) => updateArtifactIterateVideoStyle("mood", e.target.value)}>{["playful", "serious", "premium", "cozy", "dramatic", "energetic", "inspiring", "suspenseful", "mysterious", "whimsical", "futuristic", "nostalgic"].map((v) => <option key={`iter-v-mood-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Lighting</label><select value={artifactIterateVideoStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactIterateVideoStyle("lighting", e.target.value)}>{["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => <option key={`iter-v-light-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Palette mode</label><select value={artifactIterateVideoStyle.palette_mode || "muted"} onChange={(e) => updateArtifactIterateVideoStyle("palette_mode", e.target.value)}>{["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => <option key={`iter-v-pal-${v}`} value={v}>{v}</option>)}</select></div>
                                  <div><label>Output fidelity</label><select value={artifactIterateVideoStyle.output_fidelity || "standard"} onChange={(e) => updateArtifactIterateVideoStyle("output_fidelity", e.target.value)}><option value="standard">standard</option><option value="pro">pro</option></select></div>
                                  {(artifactIterateVideoStyle.palette_mode || "") === "brand" ? (
                                    <div style={{ gridColumn: "1 / -1" }}>
                                      <label>Brand colors</label>
                                      <div className="grid two">
                                        {["primary", "secondary", "accent", "background"].map((slot) => (
                                          <div key={`iter-v-color-${slot}`}>
                                            <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                                            <div className="row">
                                              <input type="color" value={artifactIterateVideoStyle?.brand_colors?.[slot] || "#000000"} onChange={(e) => updateArtifactIterateVideoBrandColor(slot, e.target.value)} style={{ width: "48px", padding: "2px", height: "38px" }} />
                                              <input value={artifactIterateVideoStyle?.brand_colors?.[slot] || ""} onChange={(e) => updateArtifactIterateVideoBrandColor(slot, e.target.value)} placeholder="#000000" />
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ) : null}
                                </div>
                              </div>
                              <div className="artifact-style-subsection">
                                <h4 className="artifact-style-subheading">Composition</h4>
                                <p className="note" style={{ marginTop: "4px" }}>
                                  Standard composition controls (pacing, motion intensity, safe zones) are applied automatically per format. Override below as needed.
                                </p>
                                <div className="grid two" style={{ marginTop: "10px" }}>
                                  <div>
                                    <label>Camera motion</label>
                                    <select value={artifactIterateVideoStyle.camera_motion || ""} onChange={(e) => updateArtifactIterateVideoStyle("camera_motion", e.target.value)}>
                                      <option value="">Auto</option>
                                      {["slow_dolly_in", "orbital_drift", "tracking_follow", "static_locked", "handheld_documentary", "push_pull_oscillate"].map((v) => (
                                        <option key={`iter-v-cam-${v}`} value={v}>{v}</option>
                                      ))}
                                    </select>
                                  </div>
                                  <div>
                                    <label>Energy level</label>
                                    <div className="row">
                                      {["low", "medium", "high"].map((level) => (
                                        <button
                                          key={`iter-v-energy-${level}`}
                                          type="button"
                                          className={(artifactIterateVideoStyle.energy_level || "medium") === level ? "primary" : "secondary"}
                                          onClick={() => updateArtifactIterateVideoStyle("energy_level", level)}
                                        >
                                          {level.charAt(0).toUpperCase() + level.slice(1)}
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ) : null}

                          <div className="row" style={{ marginTop: "8px" }}>
                            <button
                              type="button"
                              className="primary"
                              disabled={busy || isArtifactEditing}
                              onClick={onIterateArtifactEdit}
                            >
                              {isArtifactEditing ? "Iterating..." : "Iterate Artifact"}
                            </button>
                            <button type="button" className="secondary" disabled={busy || isArtifactEditing} onClick={resetArtifactEditPanel}>
                              Cancel
                            </button>
                          </div>
                        </>
                      ) : null}

                      {!isArtifactEditActive ? (
                        <>
                          {renderStoredArtifactContent(selectedStoredArtifact)}
                          <div className="row" style={{ marginTop: "8px" }}>
                            {String(selectedStoredArtifact?.kind || "").trim() === "text" ? (
                              <button
                                type="button"
                                className={artifactEditMode === "inline" ? "primary" : "secondary"}
                                disabled={busy || isArtifactEditing}
                                onClick={() => startInlineArtifactEdit(selectedStoredArtifact)}
                              >
                                Edit Inline
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className={artifactEditMode === "iterate" ? "primary" : "secondary"}
                              disabled={busy || isArtifactEditing}
                              onClick={() => startIterateArtifactEdit(selectedStoredArtifact)}
                            >
                              Iterate
                            </button>
                          </div>
                        </>
                      ) : null}
                    </>
                  ) : null}
                </>
              ) : (
                <p className="note" style={{ marginTop: "8px" }}>No artifacts for selected format.</p>
              )}
            </>
          ) : null}
        </div>
      )}

      {isAuthenticated && page === "publish" && (
        <div className="card">
          <h2>Publish</h2>
          <div>
            <label>Select Platform</label>
            <select
              value={publishSelectedPlatform}
              onChange={(e) => setPublishSelectedPlatform(e.target.value)}
              disabled={busy || isPublishPlatformsLoading || !publishPlatforms.length}
            >
              <option value="">{isPublishPlatformsLoading ? "Loading platforms..." : "Select platform"}</option>
              {publishPlatforms.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            {isPublishArtifactsLoading ? (
              <p className="note" style={{ marginTop: "6px" }}>Loading artifacts...</p>
            ) : null}
          </div>

          {!publishSelectedPlatform ? (
            <p className="note" style={{ marginTop: "12px" }}>Select a platform to load mapping fields.</p>
          ) : null}
          {publishSelectedPlatform && isPublishFieldSchemaLoading ? (
            <p className="note" style={{ marginTop: "12px" }}>Loading platform field schema...</p>
          ) : null}

          {publishSelectedPlatform && !isPublishFieldSchemaLoading && publishFieldSchema.length > 0 ? (
            <>
              <h3 style={{ marginTop: "16px" }}>Platform Fields</h3>
              <div className="publish-field-list">
                {publishFieldSchema.map((field) => {
                  const fieldKey = String(field?.field_key || "").trim();
                  const label = String(field?.label || fieldKey || "Field");
                  const rows = Array.isArray(publishFieldMappings?.[fieldKey]) ? publishFieldMappings[fieldKey] : [];
                  const acceptedFormats = Array.isArray(field?.accepted_artifact_formats)
                    ? field.accepted_artifact_formats.map((x) => String(x || "").trim()).filter(Boolean)
                    : [];
                  const filteredArtifactsForField = publishArtifacts.filter((a) => {
                    if (!acceptedFormats.length) return true;
                    return acceptedFormats.includes(String(a?.format || "").trim());
                  });
                  const canAddRow = true;

                  return (
                    <div key={`publish-field-${fieldKey}`} className="publish-field-card">
                      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                        <div>
                          <div className="row" style={{ gap: "6px" }}>
                            <h4 style={{ margin: 0 }}>
                              {label}
                              {field?.required ? <span className="publish-required-mark"> *</span> : null}
                            </h4>
                          </div>
                        </div>
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy || !canAddRow}
                          onClick={() => addPublishSourceRow(fieldKey)}
                        >
                          Add Source
                        </button>
                      </div>

                      {rows.length === 0 ? (
                        <p className="note" style={{ marginTop: "6px", marginBottom: "2px" }}>No sources mapped yet.</p>
                      ) : null}

                      {rows.map((row, idx) => {
                        const artifact = publishArtifactsById[row.artifact_id] || null;
                        const primaryPart = String(row.primary_part || "").trim();
                        const canIncludeTags = artifactHasTags(artifact);
                        return (
                          <div key={row.source_id || `${fieldKey}-${idx}`} className="publish-source-row">
                            <div className="publish-source-compact-row">
                              <div className="publish-source-artifact">
                                <label>Artifact</label>
                                <select
                                  value={row.artifact_id || ""}
                                  onChange={(e) => {
                                    const artifactId = e.target.value;
                                    const selectedArtifact = publishArtifactsById[artifactId] || null;
                                    updatePublishSourceRow(fieldKey, row.source_id, {
                                      artifact_id: artifactId,
                                      primary_part: defaultPublishPartForArtifact(selectedArtifact),
                                      include_tags: artifactHasTags(selectedArtifact) ? !!row.include_tags : false,
                                    });
                                  }}
                                >
                                  <option value="">Select artifact</option>
                                  {filteredArtifactsForField.map((a) => (
                                    <option key={a.artifact_id} value={a.artifact_id}>
                                      {`${a.title || a.artifact_id} [${a.format}]`}
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <div className="publish-source-options">
                                <label className="tag" style={{ display: "inline-flex", alignItems: "center", marginBottom: 0 }}>
                                  <input
                                    type="checkbox"
                                    checked={!!row.include_tags}
                                    disabled={!row.artifact_id || !canIncludeTags}
                                    onChange={(e) => updatePublishSourceRow(fieldKey, row.source_id, { include_tags: !!e.target.checked })}
                                    style={{ width: "auto", marginRight: "6px" }}
                                  />
                                  Include tags
                                </label>
                              </div>
                              <div className="publish-source-actions">
                                <span className="note">#{idx + 1}</span>
                                <button
                                  type="button"
                                  className="secondary"
                                  onClick={() => removePublishSourceRow(fieldKey, row.source_id)}
                                >
                                  Remove
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>

              <div className="row" style={{ marginTop: "14px" }}>
                <button
                  className="secondary"
                  type="button"
                  disabled={
                    busy
                    || !(form.project_id || "").trim()
                    || !publishSelectedPlatform
                    || !areRequiredPublishFieldsMapped
                  }
                  onClick={openSaveToPublishDialog}
                >
                  Save to Publish
                </button>
                <button className="primary" type="button" disabled>
                  Publish (Coming Soon)
                </button>
              </div>
              {!areRequiredPublishFieldsMapped ? (
                <p className="note" style={{ marginTop: "6px" }}>Map all required fields before saving.</p>
              ) : null}
              {publishSaveMessage ? <p className="note" style={{ marginTop: "8px" }}>{publishSaveMessage}</p> : null}
            </>
          ) : null}
        </div>
      )}

      {isAuthenticated && page === "publish" && showPublishSaveDialog ? (
        <div className="modal-overlay" onClick={closeSaveToPublishDialog}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>Save To Publish</h3>
            <div className="grid two">
              <div>
                <label>Name</label>
                <input
                  value={publishSaveUserName}
                  onChange={(e) => setPublishSaveUserName(e.target.value)}
                  placeholder="Enter bundle name"
                />
              </div>
              <div>
                <label>Destination Type</label>
                <select
                  value={publishSaveDestinationMode}
                  onChange={(e) => {
                    const nextMode = String(e.target.value || "url");
                    setPublishSaveDestinationMode(nextMode);
                    window.localStorage.setItem("cpublishr_publish_destination_mode", nextMode);
                  }}
                >
                  <option value="url">Enter explicit URL/path</option>
                  <option value="local">Browse local folder</option>
                </select>
              </div>
            </div>

            {publishSaveDestinationMode === "url" ? (
              <div style={{ marginTop: "10px" }}>
                <label>Output URL / Path</label>
                <input
                  value={publishSaveOutputPath}
                  onChange={(e) => {
                    const next = e.target.value;
                    setPublishSaveOutputPath(next);
                    window.localStorage.setItem("cpublishr_publish_output_path", next);
                  }}
                  placeholder="azure://container/base-prefix OR gs://bucket/prefix OR C:\\output\\folder"
                />
              </div>
            ) : (
              <div style={{ marginTop: "10px" }}>
                <label>Selected Local Folder</label>
                <input
                  value={publishSaveOutputPath}
                  onChange={(e) => {
                    const next = e.target.value;
                    setPublishSaveOutputPath(next);
                    window.localStorage.setItem("cpublishr_publish_output_path", next);
                  }}
                  placeholder="C:\\output\\folder"
                />
                <div className="row" style={{ marginTop: "8px" }}>
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy || isPublishPickingLocalPath}
                    onClick={pickPublishOutputFolder}
                  >
                    {isPublishPickingLocalPath ? "Opening..." : "Browse"}
                  </button>
                </div>
              </div>
            )}

            <div className="row" style={{ marginTop: "14px", justifyContent: "flex-end" }}>
              <button type="button" className="secondary" onClick={closeSaveToPublishDialog} disabled={busy}>
                Cancel
              </button>
              <button type="button" className="primary" onClick={onSaveToPublish} disabled={busy}>
                {busy ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      </div>
    </>
  );
}


