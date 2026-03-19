import React from "react";
import { formatOptionLabel } from "../lib/appUtils";

export default function GenerateArtifactsVideoStyleStep({
  active,
  busy,
  artifactSuggestionsLoading,
  artifactSuggestions,
  artifactVideoStyle,
  updateArtifactVideoStyle,
  artifactVideoAvoidInput,
  setArtifactVideoAvoidInput,
  addArtifactVideoAvoidTag,
  removeArtifactVideoAvoidTag,
  updateArtifactVideoBrandColor,
}) {
  if (!active) return null;

  return (
    <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
      <h3 style={{ marginTop: 0 }}>Video Style</h3>
      <p className="note" style={{ marginTop: "4px" }}>
        {artifactSuggestionsLoading ? (
          <span style={{ marginLeft: "10px", fontStyle: "italic", color: "#888" }}>
            AI suggestions are being generated...
          </span>
        ) : artifactSuggestions && artifactSuggestions.video ? (
          <span style={{ marginLeft: "10px", fontStyle: "italic", color: "#22c55e" }}>
            AI suggestions applied - edit freely
          </span>
        ) : null}
      </p>

      <div className="artifact-style-subsection">
        <h4 className="artifact-style-subheading">Creative Direction</h4>
        <div className="grid two">
          <div>
            <label>Theme<span className="publish-required-mark"> *</span></label>
            <input
              className="artifact-theme-field suggestive-placeholder"
              value={artifactVideoStyle.theme || ""}
              onChange={(e) => updateArtifactVideoStyle("theme", e.target.value)}
              placeholder='e.g. "futuristic product launch", "cozy cooking loop"'
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label>Subject / core prompt<span className="publish-required-mark"> *</span></label>
            <textarea
              className="artifact-core-prompt-field suggestive-placeholder"
              value={artifactVideoStyle.subject_prompt || ""}
              onChange={(e) => updateArtifactVideoStyle("subject_prompt", e.target.value)}
              placeholder="What should be in the video (who/what + setting + action)."
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label>Avoid / don't include</label>
            <div className="row artifact-inline-input">
              <input
                value={artifactVideoAvoidInput}
                onChange={(e) => setArtifactVideoAvoidInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addArtifactVideoAvoidTag();
                  }
                }}
                placeholder="Add tag (e.g. watermarks, logos, real people)"
              />
              <button type="button" className="secondary" onClick={addArtifactVideoAvoidTag} disabled={busy}>
                Add
              </button>
            </div>
            <div className="row" style={{ marginTop: "6px" }}>
              {(artifactVideoStyle.avoid || []).map((tag) => (
                <span key={`video-avoid-${tag}`} className="tag">
                  {tag}
                  <button type="button" onClick={() => removeArtifactVideoAvoidTag(tag)} aria-label={`Remove ${tag}`}>
                    x
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="artifact-style-subsection">
        <h4 className="artifact-style-subheading">Visual Display</h4>
        <div className="grid two">
          <div>
            <label>Mood</label>
            <select value={artifactVideoStyle.mood || "energetic"} onChange={(e) => updateArtifactVideoStyle("mood", e.target.value)}>
              {["playful", "serious", "premium", "cozy", "dramatic", "energetic", "inspiring", "suspenseful", "mysterious", "whimsical", "futuristic", "nostalgic"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Lighting</label>
            <select value={artifactVideoStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactVideoStyle("lighting", e.target.value)}>
              {["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Palette mode</label>
            <select value={artifactVideoStyle.palette_mode || "muted"} onChange={(e) => updateArtifactVideoStyle("palette_mode", e.target.value)}>
              {["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Output fidelity</label>
            <select value={artifactVideoStyle.output_fidelity || "standard"} onChange={(e) => updateArtifactVideoStyle("output_fidelity", e.target.value)}>
              <option value="standard">{formatOptionLabel("standard")}</option>
              <option value="pro">{formatOptionLabel("pro")}</option>
            </select>
          </div>
          {(artifactVideoStyle.palette_mode || "") === "brand" ? (
            <div style={{ gridColumn: "1 / -1" }}>
              <label>Brand colors</label>
              <div className="grid two">
                {["primary", "secondary", "accent", "background"].map((slot) => (
                  <div key={`video-color-${slot}`}>
                    <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                    <div className="row">
                      <input
                        type="color"
                        value={artifactVideoStyle?.brand_colors?.[slot] || "#000000"}
                        onChange={(e) => updateArtifactVideoBrandColor(slot, e.target.value)}
                        style={{ width: "48px", padding: "2px", height: "38px" }}
                      />
                      <input
                        value={artifactVideoStyle?.brand_colors?.[slot] || ""}
                        onChange={(e) => updateArtifactVideoBrandColor(slot, e.target.value)}
                        placeholder="#000000"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="artifact-style-subsection">
        <h4 className="artifact-style-subheading">Composition</h4>
        <p className="note" style={{ marginTop: "4px" }}>
          Standard composition controls (pacing, motion intensity, safe zones) are applied automatically per format. Override below as needed.
        </p>
        <div className="grid two" style={{ marginTop: "10px" }}>
          <div>
            <label>Camera motion</label>
            <select value={artifactVideoStyle.camera_motion || ""} onChange={(e) => updateArtifactVideoStyle("camera_motion", e.target.value)}>
              <option value="">Auto</option>
              {["slow_dolly_in", "orbital_drift", "tracking_follow", "static_locked", "handheld_documentary", "push_pull_oscillate"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Energy level</label>
            <div className="row">
              {["low", "medium", "high"].map((level) => (
                <button
                  key={level}
                  type="button"
                  className={(artifactVideoStyle.energy_level || "medium") === level ? "primary" : "secondary"}
                  onClick={() => updateArtifactVideoStyle("energy_level", level)}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
