import React, { useEffect, useMemo, useState } from "react";

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

const AUDIENCE_OPTIONS = ["", "builders", "founders", "enterprise", "general tech"];
const DEPTH_OPTIONS = ["", "surface", "intermediate", "deep"];
const TONE_OPTIONS = ["professional", "analytical", "conversational"];
const TARGETS = ["linkedin", "x", "youtube", "instagram", "substack", "medium", "github"];
const ARTIFACT_FORMATS_BY_KIND = {
  text: [
    "caption",
    "x_post",
    "x_thread",
    "blog_short",
    "blog_long",
    "newsletter",
    "script_short",
    "script_long",
    "hook_bank",
    "headline_variants",
    "cta_variants",
    "faq",
    "playbook",
  ],
  image: [
    "image_prompt_pack",
    "thumbnail_prompt",
    "cover_prompt",
    "carousel_prompt_pack",
    "image",
    "thumbnail",
    "cover",
  ],
  video: [
    "storyboard",
    "shotlist",
    "edit_decision_list",
    "subtitle_srt",
    "video",
  ],
  audio: [
    "voiceover_script",
    "voiceover_audio",
  ],
  gif: [
    "gif_storyboard",
    "gif_loop",
  ],
  bundle: ["bundle"],
};

async function apiRequest(baseUrl, method, path, body) {
  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
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
    target_audience: "builders",
    content_depth: "intermediate",
    tone_preference: "conversational",
    distribution_targets: ["linkedin", "github"],
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
  const [artifactOutput, setArtifactOutput] = useState(null);
  const [selectedArtifactTab, setSelectedArtifactTab] = useState(0);
  const [storedArtifacts, setStoredArtifacts] = useState([]);
  const [selectedStoredFormat, setSelectedStoredFormat] = useState("");
  const [selectedStoredArtifactTab, setSelectedStoredArtifactTab] = useState(0);
  const [isArtifactGenerating, setIsArtifactGenerating] = useState(false);
  const [isStoredArtifactsLoading, setIsStoredArtifactsLoading] = useState(false);

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
    const seen = new Set();
    const out = [];
    for (const a of storedArtifacts) {
      const fmt = (a?.format || "").trim();
      if (fmt && !seen.has(fmt)) {
        seen.add(fmt);
        out.push(fmt);
      }
    }
    return out.sort();
  }, [storedArtifacts]);
  const filteredStoredArtifacts = useMemo(() => {
    if (!selectedStoredFormat) return [];
    return storedArtifacts.filter((a) => a?.format === selectedStoredFormat);
  }, [storedArtifacts, selectedStoredFormat]);
  const selectedStoredArtifact = filteredStoredArtifacts[selectedStoredArtifactTab] || null;

  async function refreshVersions(projectId, preferredVersion) {
    const data = await apiRequest(apiBaseUrl, "GET", `/api/v1/versions/${projectId}`);
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

  async function checkExistingContent(projectId) {
    if (!(projectId || "").trim()) {
      setHasExistingContent(false);
      return;
    }
    setIsCheckingProjectData(true);
    try {
      const data = await apiRequest(apiBaseUrl, "GET", `/api/v1/versions/${projectId}`);
      const list = data?.versions || [];
      const exists = Array.isArray(list) && list.length > 0;
      setHasExistingContent(exists);
      setShowGenerateSetupForm(!exists);
    } catch {
      setHasExistingContent(false);
      setShowGenerateSetupForm(true);
    } finally {
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

  function toggleArtifactFormat(format) {
    const current = new Set(selectedArtifactFormats);
    if (current.has(format)) current.delete(format);
    else current.add(format);
    setSelectedArtifactFormats(Array.from(current));
  }

  function toggleArtifactKind(kind) {
    const formats = ARTIFACT_FORMATS_BY_KIND[kind] || [];
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
      setNodeAudit((prev) => [...prev, { node: "Node 0 - Topic Initialization", status: "running", output: null }]);
      const node0 = await apiRequest(apiBaseUrl, "POST", "/api/v1/projects/", form);
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 0 - Topic Initialization", status: "completed", output: node0 };
        return next;
      });

      setNodeAudit((prev) => [...prev, { node: "Node 1 - Research Trends", status: "running", output: null }]);
      const node1 = await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/nodes/research", {
        topic: form,
        persist_context: false,
      });
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 1 - Research Trends", status: "completed", output: node1 };
        return next;
      });

      setNodeAudit((prev) => [...prev, { node: "Node 2 - Master Content", status: "running", output: null }]);
      const node2 = await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/nodes/master", {
        topic: form,
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
      await apiRequest(
        apiBaseUrl,
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
      const out = await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/nodes/editorial/save-inline", {
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
      const out = await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/nodes/editorial/feedback/preview", {
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
    setBusy(true);
    try {
      await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: selectedVersion.version_number,
      });
      setMessage(`Finalized version v${selectedVersion.version_number}.`);
      setPage("artifacts");
    } catch (e) {
      setError(e.message || String(e));
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
    setBusy(true);
    try {
      await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: saved.draft_version,
      });
      await refreshVersions(form.project_id, saved.draft_version);
      setMessage(`Saved and finalized version v${saved.draft_version}.`);
      setPage("artifacts");
    } catch (e) {
      setError(e.message || String(e));
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
    setBusy(true);
    try {
      await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: saved.draft_version,
      });
      await refreshVersions(form.project_id, saved.draft_version);
      setMessage(`Saved and finalized version v${saved.draft_version}.`);
      setPage("artifacts");
    } catch (e) {
      setError(e.message || String(e));
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
    setArtifactOutput(null);
    setSelectedArtifactTab(0);
    try {
      const out = await apiRequest(apiBaseUrl, "POST", "/api/v1/artifacts/generate", {
        project_id: form.project_id,
        requested_formats: selectedArtifactFormats,
        stages: {
          plan: true,
          prompt_pack: true,
          render_media: true,
          assemble: true,
          package: true,
        },
        revision_mode: "new_revision",
        style_settings: {},
      });
      setArtifactOutput(out);
      setSelectedArtifactTab(0);
      const count = Array.isArray(out?.artifacts) ? out.artifacts.length : 0;
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
    try {
      const out = await apiRequest(apiBaseUrl, "GET", `/api/v1/artifacts/${form.project_id}`);
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setStoredArtifacts(items);
      const formats = Array.from(new Set(items.map((a) => (a?.format || "").trim()).filter(Boolean))).sort();
      setSelectedStoredFormat(formats[0] || "");
      setSelectedStoredArtifactTab(0);
      const count = Array.isArray(out?.artifacts) ? out.artifacts.length : 0;
      setMessage(`Loaded ${count} stored artifact(s).`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setIsStoredArtifactsLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedVersion) return;
    setWorkingContent(selectedVersion.content || "");
    setFeedbackPreviewContent("");
  }, [selectedVersionNumber]);

  useEffect(() => {
    const projectId = (form.project_id || "").trim();
    checkExistingContent(projectId);
  }, [form.project_id, apiBaseUrl]);

  return (
    <div className="container">
      <div className="card">
        <h1>CPublishr UI</h1>
        <p className="note">Lightweight React interface for Node 0-3 flow with editorial actions.</p>
          <div className="grid two">
            <div>
              <label>Backend Base URL</label>
              <input value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} />
            </div>
            <div>
              <label>Project ID</label>
              <input value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} />
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

      {page === "setup" && showGenerateSetupForm && (
        <div className="card">
          <h2>Initialize + Generate Content</h2>
          <div className="grid two">
            <div>
              <label>Topic Title (required)</label>
              <input value={form.topic_title} onChange={(e) => setForm({ ...form, topic_title: e.target.value })} />
            </div>
            <div>
              <label>Core Idea (required)</label>
              <input value={form.core_idea} onChange={(e) => setForm({ ...form, core_idea: e.target.value })} />
            </div>
            <div>
              <label>Target Audience</label>
              <select value={form.target_audience} onChange={(e) => setForm({ ...form, target_audience: e.target.value || null })}>
                {AUDIENCE_OPTIONS.map((x) => <option key={x || "none"} value={x}>{x || "(none)"}</option>)}
              </select>
            </div>
            <div>
              <label>Content Depth</label>
              <select value={form.content_depth} onChange={(e) => setForm({ ...form, content_depth: e.target.value || null })}>
                {DEPTH_OPTIONS.map((x) => <option key={x || "none"} value={x}>{x || "(none)"}</option>)}
              </select>
            </div>
            <div>
              <label>Tone Preference (required)</label>
              <select value={form.tone_preference} onChange={(e) => setForm({ ...form, tone_preference: e.target.value })}>
                {TONE_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
              </select>
            </div>
            <div>
              <label>Distribution Targets (required)</label>
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
          <label>User Content (optional)</label>
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

      {page === "editorial" && (
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

      {page === "artifacts" && (
        <div className="card">
          <h2>Artifact Generator</h2>
          <p className="note">Select one or more formats and generate artifacts from finalized content.</p>
          <label>Artifact Formats by Kind</label>
          {Object.entries(ARTIFACT_FORMATS_BY_KIND).map(([kind, formats]) => {
            const selectedCount = formats.filter((fmt) => selectedArtifactFormats.includes(fmt)).length;
            const allSelected = selectedCount === formats.length;
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
            <button className="secondary" disabled={busy} onClick={onViewStoredArtifacts}>
              {isStoredArtifactsLoading ? "Loading Stored Artifacts..." : "View Stored Artifacts"}
            </button>
            <button className="secondary" disabled={busy} onClick={() => setPage("editorial")}>Back to Editorial</button>
          </div>
          {generatedArtifacts.length > 0 ? (
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
          {storedArtifacts.length > 0 ? (
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
