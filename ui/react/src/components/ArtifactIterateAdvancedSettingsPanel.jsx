import React from "react";
import { formatOptionLabel } from "../lib/appUtils";

export default function ArtifactIterateAdvancedSettingsPanel({
  active,
  selectedStoredArtifact,
  artifactIterateFormatAdvanced,
  updateArtifactIterateAdvanced,
}) {
  if (!active) return null;

  const format = String(selectedStoredArtifact?.format || "");

  return (
    <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
      <h3 style={{ marginTop: 0 }}>Format-specific Advanced Settings (optional)</h3>
      <div className="grid two">
        {format === "post" ? (
          <>
            <div><label>length</label><select value={artifactIterateFormatAdvanced?.post?.length || "medium"} onChange={(e) => updateArtifactIterateAdvanced("post", "length", e.target.value)}><option value="short">{formatOptionLabel("short")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="long">{formatOptionLabel("long")}</option></select></div>
            <div><label>structure_hint</label><select value={artifactIterateFormatAdvanced?.post?.structure_hint || "framework-led"} onChange={(e) => updateArtifactIterateAdvanced("post", "structure_hint", e.target.value)}><option value="framework-led">{formatOptionLabel("framework-led")}</option><option value="story-led">{formatOptionLabel("story-led")}</option><option value="list-led">{formatOptionLabel("list-led")}</option></select></div>
            <div><label>cta_strength</label><select value={artifactIterateFormatAdvanced?.post?.cta_strength || "medium"} onChange={(e) => updateArtifactIterateAdvanced("post", "cta_strength", e.target.value)}><option value="soft">{formatOptionLabel("soft")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="strong">{formatOptionLabel("strong")}</option></select></div>
          </>
        ) : null}
        {format === "caption" ? (
          <>
            <div><label>length</label><select value={artifactIterateFormatAdvanced?.caption?.length || "short"} onChange={(e) => updateArtifactIterateAdvanced("caption", "length", e.target.value)}><option value="short">{formatOptionLabel("short")}</option><option value="medium">{formatOptionLabel("medium")}</option></select></div>
            <div><label>emoji_density</label><select value={artifactIterateFormatAdvanced?.caption?.emoji_density || "light"} onChange={(e) => updateArtifactIterateAdvanced("caption", "emoji_density", e.target.value)}><option value="none">{formatOptionLabel("none")}</option><option value="light">{formatOptionLabel("light")}</option><option value="moderate">{formatOptionLabel("moderate")}</option></select></div>
          </>
        ) : null}
        {format === "newsletter" ? (
          <>
            <div><label>sections</label><input type="number" min="3" max="6" value={artifactIterateFormatAdvanced?.newsletter?.sections || 4} onChange={(e) => updateArtifactIterateAdvanced("newsletter", "sections", Number(e.target.value))} /></div>
            <div><label>takeaway_bullets</label><input type="number" min="3" max="6" value={artifactIterateFormatAdvanced?.newsletter?.takeaway_bullets || 4} onChange={(e) => updateArtifactIterateAdvanced("newsletter", "takeaway_bullets", Number(e.target.value))} /></div>
          </>
        ) : null}
        {format === "blog" ? (
          <>
            <div><label>seo_intent</label><select value={artifactIterateFormatAdvanced?.blog?.seo_intent || "informational"} onChange={(e) => updateArtifactIterateAdvanced("blog", "seo_intent", e.target.value)}><option value="informational">{formatOptionLabel("informational")}</option><option value="how-to">{formatOptionLabel("how-to")}</option><option value="comparison">{formatOptionLabel("comparison")}</option></select></div>
            <div><label>faq_count</label><input type="number" min="0" max="5" value={artifactIterateFormatAdvanced?.blog?.faq_count || 3} onChange={(e) => updateArtifactIterateAdvanced("blog", "faq_count", Number(e.target.value))} /></div>
          </>
        ) : null}
        {format === "script_short" ? (
          <>
            <div><label>target_duration_sec</label><input type="number" min="10" max="120" value={artifactIterateFormatAdvanced?.script_short?.target_duration_sec || 30} onChange={(e) => updateArtifactIterateAdvanced("script_short", "target_duration_sec", Number(e.target.value))} /></div>
            <div><label>pacing</label><select value={artifactIterateFormatAdvanced?.script_short?.pacing || "normal"} onChange={(e) => updateArtifactIterateAdvanced("script_short", "pacing", e.target.value)}><option value="slow">{formatOptionLabel("slow")}</option><option value="normal">{formatOptionLabel("normal")}</option><option value="fast">{formatOptionLabel("fast")}</option></select></div>
          </>
        ) : null}
        {format === "cta_variants" ? (
          <>
            <div><label>variant_count</label><input type="number" min="7" max="11" value={artifactIterateFormatAdvanced?.cta_variants?.variant_count || 7} onChange={(e) => updateArtifactIterateAdvanced("cta_variants", "variant_count", Number(e.target.value))} /></div>
            <div><label>angles (comma-separated)</label><input value={Array.isArray(artifactIterateFormatAdvanced?.cta_variants?.angles) ? artifactIterateFormatAdvanced.cta_variants.angles.join(", ") : ""} onChange={(e) => updateArtifactIterateAdvanced("cta_variants", "angles", String(e.target.value || "").split(",").map((x) => x.trim()).filter(Boolean))} /></div>
          </>
        ) : null}
      </div>
    </div>
  );
}
