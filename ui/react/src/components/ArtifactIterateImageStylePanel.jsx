import React from "react";
import { formatOptionLabel } from "../lib/appUtils";

export default function ArtifactIterateImageStylePanel({
  active,
  artifactIterateImageStyle,
  updateArtifactIterateImageStyle,
  updateArtifactIterateImageBrandColor,
}) {
  if (!active) return null;

  return (
    <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
      <h3 style={{ marginTop: 0 }}>Image Style</h3>
      <div className="artifact-style-subsection">
        <h4 className="artifact-style-subheading">Visual Display</h4>
        <div className="grid two">
          <div><label>Medium</label><select value={artifactIterateImageStyle.medium || "illustration"} onChange={(e) => updateArtifactIterateImageStyle("medium", e.target.value)}>{["photo", "illustration", "3d_render", "comic", "watercolor", "oil_paint", "vector_flat", "pixel_art"].map((v) => <option key={`iter-img-med-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Texture</label><select value={artifactIterateImageStyle.texture || "clean"} onChange={(e) => updateArtifactIterateImageStyle("texture", e.target.value)}>{["clean", "film_grain", "halftone", "paper", "canvas", "noise"].map((v) => <option key={`iter-img-tex-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Lighting</label><select value={artifactIterateImageStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactIterateImageStyle("lighting", e.target.value)}>{["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => <option key={`iter-img-light-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Palette mode</label><select value={artifactIterateImageStyle.palette_mode || "muted"} onChange={(e) => updateArtifactIterateImageStyle("palette_mode", e.target.value)}>{["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => <option key={`iter-img-pal-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Output fidelity</label><select value={artifactIterateImageStyle.output_fidelity || "standard"} onChange={(e) => updateArtifactIterateImageStyle("output_fidelity", e.target.value)}><option value="standard">{formatOptionLabel("standard")}</option><option value="hd">{formatOptionLabel("hd")}</option></select></div>
          {(artifactIterateImageStyle.palette_mode || "") === "brand" ? (
            <div style={{ gridColumn: "1 / -1" }}>
              <label>Brand colors</label>
              <div className="grid two">
                {["primary", "secondary", "accent", "background"].map((slot) => (
                  <div key={`iter-img-color-${slot}`}>
                    <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                    <div className="row">
                      <input type="color" value={artifactIterateImageStyle?.brand_colors?.[slot] || "#000000"} onChange={(e) => updateArtifactIterateImageBrandColor(slot, e.target.value)} style={{ width: "48px", padding: "2px", height: "38px" }} />
                      <input value={artifactIterateImageStyle?.brand_colors?.[slot] || ""} onChange={(e) => updateArtifactIterateImageBrandColor(slot, e.target.value)} placeholder="#000000" />
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
        <div className="grid two">
          <div><label>Mood</label><select value={artifactIterateImageStyle.mood || "premium"} onChange={(e) => updateArtifactIterateImageStyle("mood", e.target.value)}>{["playful", "serious", "premium", "cozy", "dramatic", "energetic"].map((v) => <option key={`iter-img-mood-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
          <div><label>Focus / negative space</label><select value={artifactIterateImageStyle.focus_negative_space || "subject_centered"} onChange={(e) => updateArtifactIterateImageStyle("focus_negative_space", e.target.value)}>{["subject_centered", "rule_of_thirds", "negative_space_left", "negative_space_right"].map((v) => <option key={`iter-img-focus-${v}`} value={v}>{formatOptionLabel(v)}</option>)}</select></div>
        </div>
      </div>
    </div>
  );
}
