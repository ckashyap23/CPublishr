import { formatOptionLabel } from "../lib/appUtils";

export default function ArtifactIterateTextStylePanel({
  active,
  artifactIterateStyleSource,
  setArtifactIterateStyleSource,
  artifactIterateVoiceProfileId,
  setArtifactIterateVoiceProfileId,
  approvedActiveVoiceProfileOptions,
  artifactIterateVoiceStyleTextareaRef,
  artifactIterateManualCoreVoice,
  setArtifactIterateManualCoreVoice,
  autoResizeTextarea,
  artifactIterateToneNuance,
  updateArtifactIterateToneNuance,
  projectToneBase,
  artifactIterateFrameworkMode,
  setArtifactIterateFrameworkMode,
}) {
  if (!active) return null;

  return (
    <>
      <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
        <h3 style={{ marginTop: 0 }}>Style Source</h3>
        <div className="row">
          <label className="tag">
            <input
              type="radio"
              name="artifact-iterate-style-source"
              checked={artifactIterateStyleSource === "voice_profile"}
              onChange={() => setArtifactIterateStyleSource("voice_profile")}
              style={{ width: "auto", marginRight: "6px" }}
            />
            Use saved Voice Profile
          </label>
          <label className="tag">
            <input
              type="radio"
              name="artifact-iterate-style-source"
              checked={artifactIterateStyleSource === "manual"}
              onChange={() => setArtifactIterateStyleSource("manual")}
              style={{ width: "auto", marginRight: "6px" }}
            />
            Enter style manually
          </label>
        </div>
        {artifactIterateStyleSource === "voice_profile" ? (
          <div style={{ marginTop: "8px" }}>
            <label>voice_profile_id</label>
            <select value={artifactIterateVoiceProfileId} onChange={(e) => setArtifactIterateVoiceProfileId(e.target.value)}>
              <option value="">Select voice profile</option>
              {approvedActiveVoiceProfileOptions.map((opt) => (
                <option key={`iter-vp-${opt.value}`} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        ) : (
          <div style={{ marginTop: "8px" }}>
            <label>Voice Style</label>
            <textarea
              ref={artifactIterateVoiceStyleTextareaRef}
              className="artifact-edit-textarea"
              value={artifactIterateManualCoreVoice}
              onChange={(e) => {
                setArtifactIterateManualCoreVoice(e.target.value);
                autoResizeTextarea(e.target);
              }}
              placeholder="How should this revised artifact sound?"
            />
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
        <h3 style={{ marginTop: 0 }}>Tone Nuances</h3>
        <div className="grid two">
          {[
            ["directness", "Directness", "soft", "direct"],
            ["warmth", "Warmth", "neutral", "warm"],
            ["energy", "Energy", "calm", "high-energy"],
            ["authority", "Authority", "exploratory", "decisive"],
          ].map(([key, label, left, right]) => (
            <div key={`iter-tone-${key}`}>
              <label>{label}</label>
              <input
                type="range"
                min="0"
                max="4"
                step="1"
                value={Number(artifactIterateToneNuance[key] ?? 2)}
                onChange={(e) => updateArtifactIterateToneNuance(key, Number(e.target.value))}
              />
              <div className="row note" style={{ justifyContent: "space-between" }}>
                <span>{`${left} <-> ${right}`}</span>
                <span>{artifactIterateToneNuance[key] ?? 2}/4</span>
              </div>
            </div>
          ))}
          {projectToneBase === "analytical" ? (
            <>
              <div>
                <label>Rigor</label>
                <input type="range" min="0" max="4" step="1" value={Number(artifactIterateToneNuance.rigor ?? 3)} onChange={(e) => updateArtifactIterateToneNuance("rigor", Number(e.target.value))} />
              </div>
              <div>
                <label>Abstraction</label>
                <input type="range" min="0" max="4" step="1" value={Number(artifactIterateToneNuance.abstraction ?? 2)} onChange={(e) => updateArtifactIterateToneNuance("abstraction", Number(e.target.value))} />
              </div>
              <div>
                <label>Framework mode</label>
                <select value={artifactIterateFrameworkMode} onChange={(e) => setArtifactIterateFrameworkMode(e.target.value)}>
                  <option value="none">{formatOptionLabel("none")}</option>
                  <option value="light">{formatOptionLabel("light")}</option>
                  <option value="strong">{formatOptionLabel("strong")}</option>
                </select>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}
