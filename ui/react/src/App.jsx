import React, { useEffect, useMemo, useState } from "react";

const API_BASE_DEFAULT = "http://127.0.0.1:8010";

const DEFAULT_USER_CONTENT = "Imagine your content as a movie script: you write one master doc, and a crew of AI agents turns it into trailers, posters, and behind-the-scenes clips automatically. One agent makes a punchy LinkedIn post, another crafts an Instagram carousel, a third writes a Twitter/X thread, and a fourth adapts it into a YouTube short script. Same core story, different costumes, different stage. The fun part? You stop rewriting from scratch and start directing the message while your agents handle the platform-specific polish.";

const AUDIENCE_OPTIONS = ["", "builders", "founders", "enterprise", "general tech"];
const DEPTH_OPTIONS = ["", "surface", "intermediate", "deep"];
const TONE_OPTIONS = ["professional", "analytical", "conversational"];
const TARGETS = ["linkedin", "x", "youtube", "instagram", "substack", "medium", "github"];

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

  const [form, setForm] = useState({
    project_id: "proj_local_1",
    topic_title: "AI Multi-Agent Content",
    core_idea: "One master doc, many platform outputs",
    user_content: DEFAULT_USER_CONTENT,
    target_audience: "builders",
    content_depth: "intermediate",
    tone_preference: "professional",
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

  const selectedVersion = useMemo(
    () => versions.find((v) => v.version_number === selectedVersionNumber) || null,
    [versions, selectedVersionNumber]
  );

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

  async function onGenerateContent() {
    setError("");
    setMessage("");
    setIsGenerating(true);
    setBusy(true);
    try {
      await apiRequest(apiBaseUrl, "POST", "/api/v1/projects/", form);
      await apiRequest(apiBaseUrl, "POST", "/api/v1/workflows/runs", { project_id: form.project_id });
      await refreshVersions(form.project_id);
      setMessage("Node 0-2 completed. Ready for editorial.");
      setPage("editorial");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsGenerating(false);
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

  useEffect(() => {
    if (!selectedVersion) return;
    setWorkingContent(selectedVersion.content || "");
    setFeedbackPreviewContent("");
  }, [selectedVersionNumber]);

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
          </div>
        </div>
        {message ? <div className="status ok">{message}</div> : null}
        {error ? <div className="status warn">{error}</div> : null}
      </div>

      {page === "setup" && (
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
            <button className="primary" disabled={busy} onClick={onGenerateContent}>
              {isGenerating ? "Generating..." : "Generate Content"}
            </button>
          </div>
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
          <h2>Artifacts (Placeholder)</h2>
          <p className="note">Flow pauses here for now. Links are intentionally empty placeholders.</p>
          <ul className="links">
            <li>Reel: <a href="#">(coming soon)</a></li>
            <li>Short Video: <a href="#">(coming soon)</a></li>
            <li>Voice Over Clip: <a href="#">(coming soon)</a></li>
            <li>Text Blog: <a href="#">(coming soon)</a></li>
          </ul>
          <button className="secondary" onClick={() => setPage("editorial")}>Back to Editorial</button>
        </div>
      )}

      {isGenerating && (
        <div className="loading-overlay" role="status" aria-live="polite" aria-busy="true">
          <div className="loading-panel">
            <div className="spinner" />
            <h3>Generating content</h3>
            <p className="note">Node 0-2 workflow is running. This can take a few minutes.</p>
          </div>
        </div>
      )}
    </div>
  );
}
