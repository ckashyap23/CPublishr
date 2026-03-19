export default function StoredArtifactTabs({
  filteredStoredArtifacts,
  selectedStoredFormat,
  selectedStoredArtifactTab,
  editingArtifactTitleId,
  editingArtifactTitleValue,
  setEditingArtifactTitleValue,
  saveArtifactTitle,
  cancelEditingArtifactTitle,
  startEditingArtifactTitle,
  setSelectedStoredArtifactTab,
}) {
  if (!filteredStoredArtifacts.length) return null;

  return (
    <div className="row stored-artifact-tabs" style={{ marginTop: "8px", marginBottom: "8px" }}>
      {filteredStoredArtifacts.map((artifact, idx) => (
        <div
          key={artifact.artifact_id || `stored-artifact-${idx}`}
          className={`artifact-title-chip ${idx === selectedStoredArtifactTab ? "artifact-title-chip-active" : ""}`}
        >
          {editingArtifactTitleId === artifact?.artifact_id ? (
            <div className="row stored-artifact-title-editor" style={{ gap: "6px" }}>
              <input
                className="stored-artifact-title-input"
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
  );
}
