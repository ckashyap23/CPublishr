import StoredArtifactContent from "./StoredArtifactContent";

export default function StoredArtifactReadOnly({
  artifact,
  busy,
  isArtifactEditing,
  artifactEditMode,
  startInlineArtifactEdit,
  startIterateArtifactEdit,
}) {
  if (!artifact) return null;

  return (
    <>
      <StoredArtifactContent artifact={artifact} />
      <div className="row" style={{ marginTop: "8px" }}>
        {String(artifact?.kind || "").trim() === "text" ? (
          <button
            type="button"
            className={artifactEditMode === "inline" ? "primary" : "secondary"}
            disabled={busy || isArtifactEditing}
            onClick={() => startInlineArtifactEdit(artifact)}
          >
            Edit Inline
          </button>
        ) : null}
        <button
          type="button"
          className={artifactEditMode === "iterate" ? "primary" : "secondary"}
          disabled={busy || isArtifactEditing}
          onClick={() => startIterateArtifactEdit(artifact)}
        >
          Iterate
        </button>
      </div>
    </>
  );
}
