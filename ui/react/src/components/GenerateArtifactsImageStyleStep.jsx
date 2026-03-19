import React from "react";
import { formatOptionLabel } from "../lib/appUtils";

export default function GenerateArtifactsImageStyleStep({
  active,
  busy,
  artifactSuggestionsLoading,
  artifactSuggestions,
  artifactImageStyle,
  updateArtifactImageStyle,
  artifactImageAvoidInput,
  setArtifactImageAvoidInput,
  addArtifactImageAvoidTag,
  removeArtifactImageAvoidTag,
  updateArtifactImageBrandColor,
}) {
  if (!active) return null;

  return (
    <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
      <h3 style={{ marginTop: 0 }}>Image Style</h3>
      <p className="note" style={{ marginTop: "4px" }}>
        {artifactSuggestionsLoading ? (
          <span style={{ marginLeft: "10px", fontStyle: "italic", color: "#888" }}>
            AI suggestions are being generated...
          </span>
        ) : artifactSuggestions && artifactSuggestions.image ? (
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
              value={artifactImageStyle.theme || ""}
              onChange={(e) => updateArtifactImageStyle("theme", e.target.value)}
              placeholder='e.g. "luxury chocolate", "minimal fintech", "kids comic"'
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label>Subject / core prompt<span className="publish-required-mark"> *</span></label>
            <textarea
              className="artifact-core-prompt-field suggestive-placeholder"
              value={artifactImageStyle.subject_prompt || ""}
              onChange={(e) => updateArtifactImageStyle("subject_prompt", e.target.value)}
              placeholder="What should be in the image (who/what + setting + action)."
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label>Avoid / don't include</label>
            <div className="row artifact-inline-input">
              <input
                value={artifactImageAvoidInput}
                onChange={(e) => setArtifactImageAvoidInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addArtifactImageAvoidTag();
                  }
                }}
                placeholder="Add tag (e.g. watermark, clutter, brand logos)"
              />
              <button type="button" className="secondary" onClick={addArtifactImageAvoidTag} disabled={busy}>
                Add
              </button>
            </div>
            <div className="row" style={{ marginTop: "6px" }}>
              {(artifactImageStyle.avoid || []).map((tag) => (
                <span key={tag} className="tag">
                  {tag}
                  <button type="button" onClick={() => removeArtifactImageAvoidTag(tag)} aria-label={`Remove ${tag}`}>
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
            <label>Medium</label>
            <select value={artifactImageStyle.medium || "illustration"} onChange={(e) => updateArtifactImageStyle("medium", e.target.value)}>
              {["photo", "illustration", "3d_render", "comic", "watercolor", "oil_paint", "vector_flat", "pixel_art"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Texture</label>
            <select value={artifactImageStyle.texture || "clean"} onChange={(e) => updateArtifactImageStyle("texture", e.target.value)}>
              {["clean", "film_grain", "halftone", "paper", "canvas", "noise"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Lighting</label>
            <select value={artifactImageStyle.lighting || "soft_daylight"} onChange={(e) => updateArtifactImageStyle("lighting", e.target.value)}>
              {["soft_daylight", "golden_hour", "sunset_warm", "overcast_diffused", "studio_softbox", "high_key_bright", "low_key_moody", "neon_night", "backlit_silhouette", "rim_light", "volumetric_godrays", "dramatic_spotlight"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Palette mode</label>
            <select value={artifactImageStyle.palette_mode || "muted"} onChange={(e) => updateArtifactImageStyle("palette_mode", e.target.value)}>
              {["brand", "monochrome", "pastel", "neon", "earthy", "muted", "high_contrast"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Output fidelity</label>
            <div className="row">
              <button
                type="button"
                className={(artifactImageStyle.output_fidelity || "standard") === "standard" ? "primary" : "secondary"}
                onClick={() => updateArtifactImageStyle("output_fidelity", "standard")}
              >
                Standard
              </button>
              <button
                type="button"
                className={(artifactImageStyle.output_fidelity || "standard") === "hd" ? "primary" : "secondary"}
                onClick={() => updateArtifactImageStyle("output_fidelity", "hd")}
              >
                HD
              </button>
            </div>
          </div>
          {(artifactImageStyle.palette_mode || "") === "brand" ? (
            <div style={{ gridColumn: "1 / -1" }}>
              <label>Brand colors</label>
              <div className="grid two">
                {["primary", "secondary", "accent", "background"].map((slot) => (
                  <div key={slot}>
                    <label style={{ marginBottom: "4px", fontWeight: 500 }}>{slot}</label>
                    <div className="row">
                      <input
                        type="color"
                        value={artifactImageStyle?.brand_colors?.[slot] || "#000000"}
                        onChange={(e) => updateArtifactImageBrandColor(slot, e.target.value)}
                        style={{ width: "48px", padding: "2px", height: "38px" }}
                      />
                      <input
                        value={artifactImageStyle?.brand_colors?.[slot] || ""}
                        onChange={(e) => updateArtifactImageBrandColor(slot, e.target.value)}
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
        <div className="grid two">
          <div>
            <label>Mood</label>
            <select value={artifactImageStyle.mood || "premium"} onChange={(e) => updateArtifactImageStyle("mood", e.target.value)}>
              {["playful", "serious", "premium", "cozy", "dramatic", "energetic"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Focus / negative space</label>
            <select
              value={artifactImageStyle.focus_negative_space || "subject_centered"}
              onChange={(e) => updateArtifactImageStyle("focus_negative_space", e.target.value)}
            >
              {["subject_centered", "rule_of_thirds", "negative_space_left", "negative_space_right"].map((v) => (
                <option key={v} value={v}>{formatOptionLabel(v)}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
