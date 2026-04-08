import StoredArtifactContent from "./StoredArtifactContent";

export default function GeneratedArtifactsPreview({
  active,
  generatedArtifacts,
  selectedArtifactTab,
  setSelectedArtifactTab,
  selectedGeneratedArtifact,
}) {
  if (!active || !generatedArtifacts.length) return null;

  return (
    <>
      <h3 style={{ marginTop: "16px" }}>Generated Artifacts</h3>
      <div className="row" style={{ marginBottom: "8px" }}>
        {generatedArtifacts.map((artifact, idx) => (
          <button
            key={artifact.artifact_id || `${artifact.format}-${idx}`}
            type="button"
            className={idx === selectedArtifactTab ? "primary" : "secondary"}
            onClick={() => setSelectedArtifactTab(idx)}
          >
            {artifact.format}
          </button>
        ))}
      </div>
      {selectedGeneratedArtifact ? (
        <StoredArtifactContent artifact={selectedGeneratedArtifact} />
      ) : null}
    </>
  );
}
