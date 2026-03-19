import React from "react";
import { formatOptionLabel } from "../lib/appUtils";

export default function ArtifactIterateVideoStylePanel({
  active,
  artifactIterateVideoStyle,
  updateArtifactIterateVideoStyle,
  updateArtifactIterateVideoBrandColor,
}) {
  if (!active) return null;

  return (
    <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
      <h3 style={{ marginTop: 0 }}>Video Style</h3>
      <div className="artifact-style-subsection">
        <h4 className="artifact-style-subheading">Visual Display</h4>
        <div className="grid two">
          <div><label>Mood</label><select value={artifactIterateVideoStyle.mood || "energetic"} onChange={(e) => updateArtifactIterateVideoStyle("mood", e.target.value)}>{["playful", "serious", "premium", "cozy", "dramatic", "energetic", "inspiring", "suspenseful", "mysterious", "whimsical", "futuristic", "nostalgic"].map((v) => <option key={`iter-v-mood-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Lighting</label><select value={artifactIterateVideoStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactIterateVideoStyle("lighting", e.target.value)}>{["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => <option key={`iter-v-light-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Palette mode</label><select value={artifactIterateVideoStyle.palette_mode || "muted"} onChange={(e) => updateArtifactIterateVideoStyle("palette_mode", e.target.value)}>{["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => <option key={`iter-v-pal-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Output fidelity</label><select value={artifactIterateVideoStyle.output_fidelity || "standard"} onChange={(e) => updateArtifactIterateVideoStyle("output_fidelity", e.target.value)}><option value="standard">{formatOptionLabel("standard")}</option><option value="pro">{formatOptionLabel("pro")}</option></select></div>
          {(artifactIterateVideoStyle.palette_mode || "") === "brand" ? (
            <div style={{ gridColumn: "1 / -1" }}>
              <label>Brand colors</label>
              <div className="grid two">
                {["primary", "secondary", "accent", "background"].map((slot) => (
                  <div key={`iter-v-color-${slot}`}>
                    <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                    <div className="row">
                      <input type="color" value={artifactIterateVideoStyle?.brand_colors?.[slot] || "#000000"} onChange={(e) => updateArtifactIterateVideoBrandColor(slot, e.target.value)} style={{ width: "48px", padding: "2px", height: "38px" }} />
                      <input value={artifactIterateVideoStyle?.brand_colors?.[slot] || ""} onChange={(e) => updateArtifactIterateVideoBrandColor(slot, e.target.value)} placeholder="#000000" />
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
            <select value={artifactIterateVideoStyle.camera_motion || ""} onChange={(e) => updateArtifactIterateVideoStyle("camera_motion", e.target.value)}>
              <option value="">Auto</option>
              {["slow_dolly_in", "orbital_drift", "tracking_follow", "static_locked", "handheld_documentary", "push_pull_oscillate"].map((v) => (
                <option key={`iter-v-cam-${v}`} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Energy level</label>
            <div className="row">
              {["low", "medium", "high"].map((level) => (
                <button
                  key={`iter-v-energy-${level}`}
                  type="button"
                  className={(artifactIterateVideoStyle.energy_level || "medium") === level ? "primary" : "secondary"}
                  onClick={() => updateArtifactIterateVideoStyle("energy_level", level)}
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
