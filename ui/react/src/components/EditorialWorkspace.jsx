export default function EditorialWorkspace({
  active,
  busy,
  versions,
  selectedVersionNumber,
  applySelection,
  getVersionLabel,
  selectedVersion,
  editorMode,
  editorialInlineTextareaRef,
  workingContent,
  setWorkingContent,
  autoResizeTextarea,
  onCancelEditorialEdit,
  onSaveInline,
  onFinalizeFromInline,
  setEditorMode,
  setFeedbackPreviewContent,
  onFinalizeSelected,
  feedbackPreviewContent,
  editorialFeedbackTextareaRef,
  feedbackText,
  setFeedbackText,
  isPreviewing,
  onFeedbackPreview,
  onCloseEditorialPreview,
  onSavePreview,
  onFinalizeFromPreview,
  onPatchKeywords,
  keywordsInput,
  setKeywordsInput,
}) {
  if (!active) return null;

  return (
    <div className="card">
      <h2>Editorial Workspace</h2>
      <div className="editorial-header-grid">
        <div className="editorial-version-picker">
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
        <div className="editorial-meta-grid">
          <div className="editorial-meta-item">
            <div className="editorial-meta-label">Selected kind</div>
            <div className="editorial-meta-value">{selectedVersion?.version_kind || "-"}</div>
          </div>
          <div className="editorial-meta-item">
            <div className="editorial-meta-label">Variant label</div>
            <div className="editorial-meta-value">{selectedVersion?.variant_label || "-"}</div>
          </div>
          <div className="editorial-meta-item">
            <div className="editorial-meta-label">Stage</div>
            <div className="editorial-meta-value">{selectedVersion?.version_stage || "-"}</div>
          </div>
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
                  <div className="row editorial-action-row" style={{ marginTop: "8px" }}>
                    <button className="secondary" disabled={busy} onClick={onCancelEditorialEdit}>Cancel</button>
                    <button className="secondary" disabled={busy} onClick={onSaveInline}>Save</button>
                    <button className="primary" disabled={busy} onClick={onFinalizeFromInline}>Finalize Content</button>
                  </div>
                </>
              ) : (
                <>
                  <pre className="content editorial-content-block">{selectedVersion.content || ""}</pre>
                  {editorMode === "none" ? (
                    <div className="row editorial-action-row" style={{ marginTop: "8px" }}>
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
                      {!feedbackPreviewContent ? (
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
                          <div className="row editorial-action-row" style={{ marginTop: "8px" }}>
                            <button className="secondary" disabled={busy || isPreviewing} onClick={onCancelEditorialEdit}>Cancel</button>
                            <button className="secondary" disabled={busy} onClick={onFeedbackPreview}>Preview</button>
                            {isPreviewing ? (
                              <div className="row" aria-live="polite">
                                <div className="spinner spinner-inline" />
                                <span className="note">Generating preview...</span>
                              </div>
                            ) : null}
                          </div>
                        </>
                      ) : (
                        <>
                          <h3 style={{ marginTop: "16px" }}>Preview Content</h3>
                          <pre className="content editorial-content-block">{feedbackPreviewContent}</pre>
                          <div className="row editorial-action-row" style={{ marginTop: "8px" }}>
                            <button className="secondary" disabled={busy} onClick={onCloseEditorialPreview}>Cancel</button>
                            <button className="secondary" disabled={busy} onClick={onSavePreview}>Save</button>
                            <button className="primary" disabled={busy} onClick={onFinalizeFromPreview}>Finalize Content</button>
                          </div>
                        </>
                      )}
                    </>
                  )}
                </>
              )}
            </div>

            {editorMode === "none" ? (
              <div className="editorial-keywords-panel">
                <h3>Keywords</h3>
                <div className="row">
                  {(selectedVersion.keywords || []).map((kw) => (
                    <span key={kw} className="tag">
                      {kw}
                      <button onClick={() => onPatchKeywords((selectedVersion.keywords || []).filter((x) => x !== kw))}>x</button>
                    </span>
                  ))}
                </div>
                <div className="row editorial-action-row" style={{ marginTop: "8px" }}>
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
  );
}
