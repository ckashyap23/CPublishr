import {
  ARTIFACT_FORMAT_DESCRIPTIONS,
  ARTIFACT_FORMAT_DISPLAY_ORDER,
  ARTIFACT_FORMAT_TITLES,
  ARTIFACT_TONE_BASE_DEFAULTS,
  FORMAT_ADVANCED_DEFAULTS,
} from "./appConstants";

export function makeDefaultFormatAdvancedSettings() {
  return {
    caption: { ...FORMAT_ADVANCED_DEFAULTS.caption },
    post: { ...FORMAT_ADVANCED_DEFAULTS.post },
    newsletter: { ...FORMAT_ADVANCED_DEFAULTS.newsletter },
    blog: { ...FORMAT_ADVANCED_DEFAULTS.blog },
    script_short: { ...FORMAT_ADVANCED_DEFAULTS.script_short },
    cta_variants: { ...FORMAT_ADVANCED_DEFAULTS.cta_variants, angles: [...FORMAT_ADVANCED_DEFAULTS.cta_variants.angles] },
  };
}

export function makeDefaultImageStyleSettings() {
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

export function toneBaseFromProjectTone(tonePreference) {
  const t = String(tonePreference || "").trim().toLowerCase();
  if (t === "analytical") return "analytical";
  if (t === "professional") return "professional";
  return "conversational";
}

export function makeDefaultToneNuance(toneBase) {
  const base = ARTIFACT_TONE_BASE_DEFAULTS[toneBase] || ARTIFACT_TONE_BASE_DEFAULTS.conversational;
  return { tone_base: toneBase, ...base };
}

export function clampInt(value, min, max, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, Math.round(n)));
}

export function humorLabelToSlider(value) {
  const v = String(value || "").trim().toLowerCase();
  if (v === "none") return 0;
  if (v === "playful") return 2;
  return 1;
}

export function humorSliderToLabel(value) {
  const n = Number(value);
  if (n <= 0) return "none";
  if (n >= 2) return "playful";
  return "light";
}

export function normalizeVoiceProfilePreview(detail) {
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

export function artifactFormatMeta(fmt) {
  const key = String(fmt || "").trim();
  return {
    key,
    title: ARTIFACT_FORMAT_TITLES[key] || key,
    description: ARTIFACT_FORMAT_DESCRIPTIONS[key] || "",
  };
}

export function makeDefaultVideoStyleSettings() {
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

export function defaultPublishPartForArtifact(artifact) {
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

export function artifactHasTags(artifact) {
  return Array.isArray(artifact?.tags_json) && artifact.tags_json.some((t) => String(t || "").trim());
}

export function extractImageStyleSeedFromArtifact(artifact) {
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

export function pickLatestImageStyleSeed(artifacts) {
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

export function makePublishSourceRow() {
  return {
    source_id: `src_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    artifact_id: "",
    primary_part: "",
    include_tags: false,
    render_as: "",
    order: null,
  };
}

export function orderArtifactFormats(kind, formats) {
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

export async function apiRequest(baseUrl, method, path, body, token = "") {
  const base = baseUrl == null || baseUrl === undefined ? "" : String(baseUrl).replace(/\/$/, "");
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${base}${path}`, {
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

export function encodePathSegment(value) {
  return encodeURIComponent(String(value || "").trim());
}

export function getVersionLabel(v) {
  if (v.version_kind === "base") return "base";
  if (v.version_kind === "variant") return v.variant_label || `variant v${v.version_number}`;
  if (v.version_kind === "editorial") return v.variant_label || `editorial v${v.version_number}`;
  return `version ${v.version_number}`;
}

export function uniqueStrings(values) {
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

export function formatOptionLabel(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const acronyms = new Map([
    ["3d", "3D"],
    ["hd", "HD"],
    ["ui", "UI"],
    ["seo", "SEO"],
    ["cta", "CTA"],
    ["gif", "GIF"],
    ["api", "API"],
  ]);
  return raw
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => {
      const lower = part.toLowerCase();
      if (acronyms.has(lower)) return acronyms.get(lower);
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

export function hashtagListFromArtifact(artifact) {
  const tags = uniqueStrings(artifact?.tags_json);
  const fromTags = tags.filter((t) => t.startsWith("#"));
  if (fromTags.length) return fromTags;
  const body = String(artifact?.payload_json?.body || "");
  const matches = body.match(/#[\p{L}\p{N}_]+/gu) || [];
  return uniqueStrings(matches);
}

export function topicTagListFromArtifact(artifact) {
  return uniqueStrings(artifact?.tags_json).filter((t) => !t.startsWith("#"));
}

export function imageSrcFromAsset(asset) {
  const uri = String(asset?.uri || "");
  if (/^(data:|https?:|blob:)/i.test(uri)) return uri;
  if (/^file:\/\//i.test(uri)) return uri;
  const path = String(asset?.path || "");
  if (/^[A-Za-z]:\\/.test(path)) {
    return `file:///${path.replace(/\\/g, "/")}`;
  }
  return "";
}

export function videoSrcFromAsset(asset) {
  const uri = String(asset?.uri || "");
  if (/^(data:|https?:|blob:)/i.test(uri)) return uri;
  if (/^file:\/\//i.test(uri)) return uri;
  const path = String(asset?.path || "");
  if (/^[A-Za-z]:\\/.test(path)) {
    return `file:///${path.replace(/\\/g, "/")}`;
  }
  return "";
}

export function autoResizeTextarea(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}
