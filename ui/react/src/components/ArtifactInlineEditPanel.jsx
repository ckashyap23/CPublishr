import LabelWithTooltip from "./LabelWithTooltip";

export default function ArtifactInlineEditPanel({
  active,
  artifactInlineTextareaRef,
  artifactInlineText,
  setArtifactInlineText,
  autoResizeTextarea,
  busy,
  isArtifactEditing,
  onSaveInlineArtifactEdit,
  resetArtifactEditPanel,
}) {
  if (!active) return null;

  return (
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
  );
}
