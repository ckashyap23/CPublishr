import React from "react";

export default function GenerateArtifactsFormatsStep({
  busy,
  selectedArtifactFormats,
  setArtifactGenerateStep,
  fetchAndApplyArtifactSuggestions,
  orderArtifactFormats,
  artifactFormatsByKind,
  artifactFormatMeta,
  storedArtifactCountsByFormat,
  toggleArtifactFormat,
}) {
  return (
    <>
      {["text", "image", "gif", "video", "audio"].map((kind) => {
        const formats = orderArtifactFormats(kind, artifactFormatsByKind[kind] || []);
        if (!formats.length) return null;
        const kindUnavailable = kind === "gif" || kind === "video";
        return (
          <div key={`wizard-kind-${kind}`} style={{ marginBottom: "22px", opacity: kindUnavailable ? 0.45 : 1 }}>
            <div className="row" style={{ marginBottom: "10px" }}>
              <strong style={{ textTransform: "capitalize" }}>{kind}</strong>
              {kindUnavailable ? (
                <span className="note" style={{ color: "#c0392b", fontStyle: "italic" }}>temporarily unavailable</span>
              ) : null}
            </div>
            <div className="artifact-card-grid">
              {formats.map((fmt) => {
                const card = artifactFormatMeta(fmt);
                const isSelected = selectedArtifactFormats.includes(card.key);
                const existingCount = storedArtifactCountsByFormat[card.key] || 0;
                return (
                  <button
                    key={card.key}
                    type="button"
                    className={`artifact-select-card ${isSelected ? "artifact-select-card-selected" : ""}`}
                    onClick={() => !kindUnavailable && toggleArtifactFormat(card.key)}
                    disabled={busy || kindUnavailable}
                    title={kindUnavailable ? "Video generation is temporarily unavailable" : undefined}
                    style={kindUnavailable ? { cursor: "not-allowed" } : undefined}
                  >
                    <div className="artifact-select-card-title">{card.title}</div>
                    {card.description ? <div className="artifact-select-card-desc">{card.description}</div> : null}
                    {existingCount > 0 ? <div className="artifact-select-card-count">{existingCount} existing</div> : null}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
      <div className="row" style={{ marginTop: "12px" }}>
        {selectedArtifactFormats.length ? (
          <button
            type="button"
            className="primary"
            disabled={busy}
            onClick={() => {
              setArtifactGenerateStep("style");
              fetchAndApplyArtifactSuggestions(selectedArtifactFormats);
            }}
          >
            Next: Style
          </button>
        ) : null}
      </div>
    </>
  );
}
