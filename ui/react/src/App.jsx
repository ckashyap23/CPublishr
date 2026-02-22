import React, { useEffect, useMemo, useRef, useState } from "react";

const API_BASE_DEFAULT = "http://127.0.0.1:8010";

const DEFAULT_USER_CONTENT = `When it comes to choosing a pet, the age-old debate of cats versus dogs often takes center stage. But what if we told you that cats might just be the superior choice? Let's explore why these independent furballs could rule the world of pets.

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
  { value: "", label: "(none)" },
  { value: "new", label: "New" },
  { value: "somewhat_familiar", label: "Somewhat familiar" },
  { value: "very_familiar", label: "Very familiar" },
];
const DETAIL_LEVEL_OPTIONS = [
  { value: "", label: "(none)" },
  { value: "quick_take", label: "Quick take" },
  { value: "practical", label: "Practical" },
  { value: "deep_dive", label: "Deep dive" },
];
const TONE_OPTIONS = ["professional", "analytical", "conversational"];
const STANCE_OPTIONS = ["neutral", "supportive", "contrarian", "balanced"];
const PRIMARY_GOAL_OPTIONS = ["", "educate", "thought_leadership", "promote", "entertain", "recruit", "community", "convert"];
const DESIRED_ACTION_OPTIONS = ["", "comment", "share", "follow", "click", "dm", "subscribe", "buy"];
const TARGETS = ["linkedin", "x", "youtube", "instagram", "substack", "medium", "github"];

function LabelWithTooltip({ text, tooltip }) {
  return (
    <div className="label-row">
      <label>{text}</label>
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

function getVersionLabel(v) {
  if (v.version_kind === "base") return "base";
  if (v.version_kind === "variant") return v.variant_label || `variant v${v.version_number}`;
  if (v.version_kind === "editorial") return v.variant_label || `editorial v${v.version_number}`;
  return `version ${v.version_number}`;
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
    topic_title: "Cats are better than dogs",
    core_idea: "Cats are better than dogs",
    user_content: DEFAULT_USER_CONTENT,
    target_audience_segment: "builders_developers",
    target_audience_notes: "",
    audience_familiarity: "",
    detail_level: "practical",
    tone_preference: "conversational",
    stance: "balanced",
    primary_goal: "",
    desired_action: "",
    voice_profile_id: "vp_local_1",
    constraints: null,
    distribution_targets: ["x", "instagram"],
  });
  const [constraintsText, setConstraintsText] = useState("");

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
  const [artifactsViewMode, setArtifactsViewMode] = useState("generate");

  const [vpCollections, setVpCollections] = useState([]);
  const [vpSelectedCollectionId, setVpSelectedCollectionId] = useState("");
  const [vpCollectionDetail, setVpCollectionDetail] = useState(null);
  const [vpSelectedVersionId, setVpSelectedVersionId] = useState("");
  const [vpVersionDetail, setVpVersionDetail] = useState(null);
  const [vpCreateForm, setVpCreateForm] = useState({ voice_profile_name: "", platforms: ["linkedin"] });
  const [vpGenerateForm, setVpGenerateForm] = useState({
    intended_use: "",
    datasets: [{ dataset_name: "", source_profile: "", blob_prefix: "", sample_scope_note: "" }],
  });
  const [vpStatusInput, setVpStatusInput] = useState("approved");
  const [isVpGenerating, setIsVpGenerating] = useState(false);
  const [userProjects, setUserProjects] = useState([]);
  const [isProjectsLoading, setIsProjectsLoading] = useState(false);
  const contentCheckSeqRef = useRef(0);
  const storedArtifactsCheckSeqRef = useRef(0);
  const isAuthenticated = !!authToken;

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
  const filteredStoredArtifacts = useMemo(() => {
    if (!selectedStoredFormat) return [];
    return storedArtifacts.filter((a) => a?.format === selectedStoredFormat);
  }, [storedArtifacts, selectedStoredFormat]);
  const selectedStoredArtifact = filteredStoredArtifacts[selectedStoredArtifactTab] || null;
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

  async function refreshVersions(projectId, preferredVersion) {
    const data = await request("GET", `/api/v1/versions/${projectId}`);
    const list = data?.versions || [];
    setVersions(list);
    if (preferredVersion && list.some((v) => v.version_number === preferredVersion)) {
      setSelectedVersionNumber(preferredVersion);
      return;
    }
    const base = list.find((v) => v.version_kind === "base");
    const fallback = base || list[0] || null;
    setSelectedVersionNumber(fallback ? fallback.version_number : null);
  }

  function persistAuthToken(token) {
    const next = token || "";
    setAuthToken(next);
    if (next) window.localStorage.setItem("cpublishr_token", next);
    else window.localStorage.removeItem("cpublishr_token");
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
      } else if (!hasCurrent && rows[0]?.project_id) {
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
    setMessage("Logged out.");
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
      return;
    }
    setIsCheckingProjectData(true);
    try {
      const data = await request("GET", `/api/v1/versions/${normalizedProjectId}`);
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
    let constraints = null;
    if ((constraintsText || "").trim()) {
      try {
        const parsed = JSON.parse(constraintsText);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          constraints = parsed;
        } else {
          throw new Error("Constraints must be a JSON object.");
        }
      } catch {
        throw new Error("Constraints must be valid JSON object text.");
      }
    }
    const voiceProfileId = (form.voice_profile_id || "").trim();
    if (!voiceProfileId) {
      throw new Error("Voice Profile ID is required.");
    }
    return {
      project_id: (form.project_id || "").trim(),
      topic_title: (form.topic_title || "").trim(),
      core_idea: (form.core_idea || "").trim(),
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
      constraints,
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
    const formats = artifactFormatsByKind[kind] || [];
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

  async function onRetrieveContent() {
    const projectId = (form.project_id || "").trim();
    if (!projectId) {
      setError("Project ID is required.");
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await refreshVersions(projectId);
      setPage("editorial");
      setMessage("Existing content retrieved. You can continue in Editorial.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
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

  async function onGenerateArtifacts() {
    if (!selectedArtifactFormats.length) {
      setError("Select at least one artifact format.");
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
      const includesImageGeneration = selectedArtifactFormats.includes("image_generation");
      const imageStyleSettings = includesImageGeneration
        ? {
            tool_name: "openai",
            output_formats: ["png"],
            size: "1024x1024",
            quality: "standard",
            style: "vivid",
          }
        : null;
      const out = await request("POST", "/api/v1/artifacts/generate", {
        project_id: form.project_id,
        requested_formats: selectedArtifactFormats,
        revision_mode: "new_revision",
        style_settings: {},
        style_settings_by_format: imageStyleSettings ? { image_generation: imageStyleSettings } : {},
      });
      setArtifactOutput(out);
      setSelectedArtifactTab(0);
      const count = Array.isArray(out?.artifacts) ? out.artifacts.length : 0;
      setHasStoredArtifactsForProject(count > 0 || hasStoredArtifactsForProject);
      setMessage(`Generated ${count} artifact(s).`);
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
      return;
    }
    setIsCheckingStoredArtifacts(true);
    try {
      const out = await request("GET", `/api/v1/artifacts/${normalizedProjectId}`);
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setHasStoredArtifactsForProject(items.length > 0);
    } catch {
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      setHasStoredArtifactsForProject(false);
    } finally {
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      setIsCheckingStoredArtifacts(false);
    }
  }

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
      return;
    }
    const projectId = (form.project_id || "").trim();
    setStoredArtifacts([]);
    setSelectedStoredFormat("");
    setSelectedStoredArtifactTab(0);
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

  return (
    <div className="container">
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h1>Publishr</h1>
          {isAuthenticated ? (
            <div className="row">
              <button className="secondary" disabled={busy} onClick={() => setPage("settings")}>Settings</button>
              <button className="secondary" disabled={busy} onClick={onLogout}>Logout</button>
            </div>
          ) : null}
        </div>
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
                  list="user-project-ids"
                  value={form.project_id}
                  onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                />
                <datalist id="user-project-ids">
                  {userProjects.map((p) => (
                    <option key={p.project_id} value={p.project_id} />
                  ))}
                </datalist>
                {page === "setup" && isProjectsLoading ? (
                  <p className="note" style={{ marginTop: "6px" }}>Loading your projects...</p>
                ) : null}
                {page === "setup" && hasExistingContent ? (
                  <div className="row" style={{ marginTop: "8px" }}>
                    <button className="secondary" disabled={busy || isCheckingProjectData} onClick={onRetrieveContent}>
                      Retrieve Content
                    </button>
                    <button
                      className="primary"
                      disabled={busy || isCheckingProjectData}
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
                  <button className={page === "setup" ? "primary" : "secondary"} disabled={busy} onClick={() => setPage("setup")}>Setup</button>
                  <button className={page === "editorial" ? "primary" : "secondary"} disabled={busy} onClick={() => setPage("editorial")}>Editorial</button>
                  <button className={page === "artifacts" ? "primary" : "secondary"} disabled={busy} onClick={() => setPage("artifacts")}>Artifacts</button>
                </div>
              </div>
            </>
          )}
        </div>
        {message ? <div className="status ok">{message}</div> : null}
        {error ? <div className="status warn">{error}</div> : null}
        {(isGenerating || isArtifactGenerating || isStoredArtifactsLoading) ? (
          <div style={{ marginTop: "10px" }}>
            <div className="progress-label">
              {isGenerating
                ? `Generating content (Node 0-2): ${nodeProgress}%`
                : (isArtifactGenerating ? "Generating artifacts..." : "Loading stored artifacts...")}
            </div>
            <div className="progress-track">
              <div
                className={`progress-fill ${isGenerating ? "" : "indeterminate"}`}
                style={isGenerating ? { width: `${nodeProgress}%` } : { width: "35%" }}
              />
            </div>
          </div>
        ) : null}
      </div>

      {isAuthenticated && page === "setup" && showGenerateSetupForm && (
        <div className="card">
          <h2>Generate Content</h2>
          <div className="grid two">
            <div>
              <LabelWithTooltip
                text="Topic Title (required)"
                tooltip="A short headline for your post idea. Keep it simple and specific—this is used to name and organize your content."
              />
              <input value={form.topic_title} onChange={(e) => setForm({ ...form, topic_title: e.target.value })} />
            </div>
            <div>
              <LabelWithTooltip
                text="Core Idea (required)"
                tooltip="The one-sentence point you want to make. If someone reads only this, they should understand your main message."
              />
              <input value={form.core_idea} onChange={(e) => setForm({ ...form, core_idea: e.target.value })} />
            </div>
            <div>
              <LabelWithTooltip
                text="Target Audience (required)"
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
                text="Target Audience Notes (optional)"
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
              <select value={form.audience_familiarity} onChange={(e) => setForm({ ...form, audience_familiarity: e.target.value || "" })}>
                {AUDIENCE_FAMILIARITY_OPTIONS.map((x) => <option key={x.value || "none"} value={x.value}>{x.label}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Detail Level"
                tooltip={"How detailed you want the content.\nQuick take: summary\nPractical: actionable depth\nDeep dive: thorough coverage with nuances"}
              />
              <select value={form.detail_level} onChange={(e) => setForm({ ...form, detail_level: e.target.value || null })}>
                {DETAIL_LEVEL_OPTIONS.map((x) => <option key={x.value || "none"} value={x.value}>{x.label}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Tone Preference (required)"
                tooltip="The “voice” of the writing—how it should sound. Example: conversational, formal, witty, bold, etc."
              />
              <select value={form.tone_preference} onChange={(e) => setForm({ ...form, tone_preference: e.target.value })}>
                {TONE_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Stance"
                tooltip={"The point of view you want to take.\nSupportive: agree/advocate\nNeutral: informative, balanced\nContrarian: challenge the common view\nBalanced: show both sides and conclude"}
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
              <select value={form.primary_goal} onChange={(e) => setForm({ ...form, primary_goal: e.target.value || "" })}>
                {PRIMARY_GOAL_OPTIONS.map((x) => <option key={x || "none"} value={x}>{x || "(none)"}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Desired Action"
                tooltip="What you want people to do after reading. Example: comment, share, follow, click a link, DM you, subscribe, or buy."
              />
              <select value={form.desired_action} onChange={(e) => setForm({ ...form, desired_action: e.target.value || "" })}>
                {DESIRED_ACTION_OPTIONS.map((x) => <option key={x || "none"} value={x}>{x || "(none)"}</option>)}
              </select>
            </div>
            <div>
              <LabelWithTooltip
                text="Voice Profile"
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
                text="Distribution Targets (optional)"
                tooltip="Where you might publish this. This doesn’t change the core idea—just helps us prepare formats that fit those platforms later."
              />
              <div className="row">
                {TARGETS.map((t) => (
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
          <LabelWithTooltip
            text="Constraints (JSON object, optional)"
            tooltip="Optional rules to guide the output. Use this to enforce must-have points, avoid certain phrases, or add compliance notes. Example keys: must_include, must_avoid, forbidden_claims, compliance_notes, sensitive_topics."
          />
          <textarea
            value={constraintsText}
            onChange={(e) => setConstraintsText(e.target.value)}
            placeholder='{"must_include":["..."],"must_avoid":["..."],"forbidden_claims":[],"compliance_notes":"","sensitive_topics":[]}'
          />
          <LabelWithTooltip
            text="User Content (optional)"
            tooltip="Any raw notes you already have—bullets, a rough draft, links, or context. The more specific this is, the more accurate the output will be."
          />
          <textarea value={form.user_content || ""} onChange={(e) => setForm({ ...form, user_content: e.target.value })} />
          <div className="row" style={{ marginTop: "12px" }}>
            <button className="primary" disabled={busy || isCheckingProjectData} onClick={onGenerateContent}>
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
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h2>Voice Profile Settings</h2>
              <button className="secondary" disabled={busy} onClick={() => setPage("setup")}>Back to Workflow</button>
            </div>
            {!authToken ? (
              <p className="note">Login first to access voice profile APIs.</p>
            ) : null}
          </div>

          <div className="card">
            <h3>Create Collection</h3>
            <div className="grid two">
              <div>
                <label>Voice Profile Name</label>
                <input
                  value={vpCreateForm.voice_profile_name}
                  onChange={(e) => setVpCreateForm((prev) => ({ ...prev, voice_profile_name: e.target.value }))}
                />
              </div>
              <div>
                <label>Platforms</label>
                <div className="row">
                  {TARGETS.map((p) => (
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
              <button className="secondary" disabled={busy || !authToken} onClick={() => loadVpCollections().catch(() => {})}>Refresh</button>
            </div>
          </div>

          <div className="card">
            <h3>Collections</h3>
            {vpCollections.length === 0 ? <p className="note">No voice profile collections found.</p> : null}
            <div className="row">
              {vpCollections.map((c) => (
                <button
                  key={c.voice_profile_id}
                  className={vpSelectedCollectionId === c.voice_profile_id ? "primary" : "secondary"}
                  onClick={() => setVpSelectedCollectionId(c.voice_profile_id)}
                >
                  {c.voice_profile_name}
                </button>
              ))}
            </div>
            {vpSelectedCollectionId ? (
              <p className="note" style={{ marginTop: "8px" }}>Selected collection id: {vpSelectedCollectionId}</p>
            ) : null}
          </div>

          <div className="card">
            <h3>Generate Voice Profile Version</h3>
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

          <div className="card">
            <h3>Version Controls</h3>
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
            <div className="note">
              <p>Selected kind: <strong>{selectedVersion?.version_kind || "-"}</strong></p>
              <p>Variant label: <strong>{selectedVersion?.variant_label || "-"}</strong></p>
              <p>Stage: <strong>{selectedVersion?.version_stage || "-"}</strong></p>
            </div>
          </div>

          {selectedVersion && (
            <>
              <div className="split">
                <div>
                  <h3>Content</h3>
                  {editorMode === "inline" ? (
                    <>
                      <textarea value={workingContent} onChange={(e) => setWorkingContent(e.target.value)} />
                      <div className="row" style={{ marginTop: "8px" }}>
                        <button className="secondary" disabled={busy} onClick={onSaveInline}>Save</button>
                        <button className="primary" disabled={busy} onClick={onFinalizeFromInline}>Finalize Content</button>
                      </div>
                    </>
                  ) : (
                    <>
                      <pre className="content">{selectedVersion.content || ""}</pre>
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

                      {editorMode === "iterate" && (
                        <>
                          <h3 style={{ marginTop: "16px" }}>Feedback Editor</h3>
                          <textarea value={feedbackText} onChange={(e) => setFeedbackText(e.target.value)} />
                          <div className="row" style={{ marginTop: "8px" }}>
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
                              <pre className="content">{feedbackPreviewContent}</pre>
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
              </div>
            </>
          )}
        </div>
      )}

      {isAuthenticated && page === "artifacts" && (
        <div className="card">
          <h2>Artifact Generator</h2>
          <p className="note">Select one or more formats and generate artifacts from finalized content.</p>
          <label>Artifact Formats by Kind</label>
          {["text", "image", "gif", "video", "audio"].map((kind) => {
            const formats = artifactFormatsByKind[kind] || [];
            const selectedCount = formats.filter((fmt) => selectedArtifactFormats.includes(fmt)).length;
            const allSelected = formats.length > 0 && selectedCount === formats.length;
            return (
              <div key={kind} style={{ marginBottom: "12px" }}>
                <div className="row" style={{ marginBottom: "6px" }}>
                  <strong style={{ textTransform: "capitalize" }}>{kind}</strong>
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={() => toggleArtifactKind(kind)}
                  >
                    {allSelected ? "Unselect All" : "Select All"}
                  </button>
                  <span className="note">{selectedCount}/{formats.length} selected</span>
                </div>
                <div className="row">
                  {formats.map((fmt) => (
                    <label key={fmt} className="tag">
                      <input
                        type="checkbox"
                        checked={selectedArtifactFormats.includes(fmt)}
                        onChange={() => toggleArtifactFormat(fmt)}
                        style={{ width: "auto", marginRight: "6px" }}
                      />
                      {fmt}
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
          <div className="row" style={{ marginTop: "12px" }}>
            <button className="primary" disabled={busy} onClick={onGenerateArtifacts}>
              {isArtifactGenerating ? "Generating Artifacts..." : "Generate Artifacts"}
            </button>
            <button
              className="secondary"
              disabled={busy || isCheckingStoredArtifacts || !hasStoredArtifactsForProject}
              onClick={onViewStoredArtifacts}
            >
              {isStoredArtifactsLoading ? "Loading Stored Artifacts..." : "View Stored Artifacts"}
            </button>
          </div>
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
              <div className="grid two">
                <div>
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
              </div>
              {filteredStoredArtifacts.length > 0 ? (
                <>
                  <div className="row" style={{ marginTop: "8px", marginBottom: "8px" }}>
                    {filteredStoredArtifacts.map((artifact, idx) => (
                      <button
                        key={`${artifact.artifact_id || selectedStoredFormat}-${idx}`}
                        type="button"
                        className={idx === selectedStoredArtifactTab ? "primary" : "secondary"}
                        onClick={() => setSelectedStoredArtifactTab(idx)}
                      >
                        {artifact.title || `${selectedStoredFormat} #${idx + 1}`}
                      </button>
                    ))}
                  </div>
                  {selectedStoredArtifact ? (
                    <pre className="content">{JSON.stringify(selectedStoredArtifact, null, 2)}</pre>
                  ) : null}
                </>
              ) : (
                <p className="note" style={{ marginTop: "8px" }}>No artifacts for selected format.</p>
              )}
            </>
          ) : null}
        </div>
      )}

    </div>
  );
}


