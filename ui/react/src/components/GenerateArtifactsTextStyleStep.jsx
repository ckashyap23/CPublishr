import React from "react";
import { formatOptionLabel } from "../lib/appUtils";

export default function GenerateArtifactsTextStyleStep({
  active,
  projectHasSavedVoiceProfileOption,
  artifactStyleSource,
  setArtifactStyleSource,
  artifactStyleVoiceProfileId,
  setArtifactStyleVoiceProfileId,
  setArtifactStyleVoiceProfileDetail,
  approvedActiveVoiceProfileOptions,
  isArtifactStyleVoiceProfileLoading,
  artifactSelectedVoiceProfilePreview,
  artifactManualCoreVoice,
  setArtifactManualCoreVoice,
  projectToneBase,
  artifactToneNuance,
  updateArtifactToneNuance,
  artifactFrameworkMode,
  setArtifactFrameworkMode,
  humorLabelToSlider,
  humorSliderToLabel,
  artifactSelectedAdvancedFormatCards,
  artifactFormatAdvanced,
  artifactAdvancedOpen,
  toggleArtifactAdvancedDrawer,
  updateArtifactAdvanced,
  toggleArtifactAdvancedAngle,
}) {
  if (!active) return null;

  return (
    <>
      <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
        <h3 style={{ marginTop: 0 }}>Style Source</h3>
        {projectHasSavedVoiceProfileOption ? (
          <div className="row">
            <label className="tag">
              <input
                type="radio"
                name="artifact-style-source"
                checked={artifactStyleSource === "voice_profile"}
                onChange={() => setArtifactStyleSource("voice_profile")}
                style={{ width: "auto", marginRight: "6px" }}
              />
              Use saved Voice Profile
            </label>
            <label className="tag">
              <input
                type="radio"
                name="artifact-style-source"
                checked={artifactStyleSource === "manual"}
                onChange={() => setArtifactStyleSource("manual")}
                style={{ width: "auto", marginRight: "6px" }}
              />
              Enter style manually
            </label>
          </div>
        ) : null}

        {projectHasSavedVoiceProfileOption && artifactStyleSource === "voice_profile" ? (
          <>
            <div style={{ marginTop: "10px" }}>
              <label>voice_profile_id<span className="publish-required-mark"> *</span></label>
              <select
                value={artifactStyleVoiceProfileId}
                onChange={(e) => {
                  setArtifactStyleVoiceProfileId(e.target.value);
                  setArtifactStyleVoiceProfileDetail(null);
                }}
              >
                <option value="">Select voice profile</option>
                {approvedActiveVoiceProfileOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            {isArtifactStyleVoiceProfileLoading ? (
              <p className="note" style={{ marginTop: "8px" }}>Loading voice profile preview...</p>
            ) : null}
            {artifactSelectedVoiceProfilePreview ? (
              <div className="artifact-style-preview">
                <div className="grid two">
                  <div>
                    <label>Voice Style Summary</label>
                    <div className="artifact-preview-box">{artifactSelectedVoiceProfilePreview.core_voice || "not specified"}</div>
                  </div>
                  <div>
                    <label>tone baseline + key traits</label>
                    <pre className="content" style={{ marginTop: "6px" }}>
{JSON.stringify({
  tone_baseline: artifactSelectedVoiceProfilePreview.tone_baseline || {},
  style_summary: artifactSelectedVoiceProfilePreview.style_summary || {},
}, null, 2)}
                    </pre>
                  </div>
                </div>
                <div className="grid two" style={{ marginTop: "8px" }}>
                  <div>
                    <label>Do highlights</label>
                    <div className="artifact-preview-box">
                      {(artifactSelectedVoiceProfilePreview.do_rules || []).slice(0, 6).map((x, i) => <div key={`do-${i}`}>- {x}</div>)}
                    </div>
                  </div>
                  <div>
                    <label>Don't highlights</label>
                    <div className="artifact-preview-box">
                      {(artifactSelectedVoiceProfilePreview.dont_rules || []).slice(0, 6).map((x, i) => <div key={`dont-${i}`}>- {x}</div>)}
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </>
        ) : (
          <div style={{ marginTop: "10px" }}>
            <label>Voice Style<span className="publish-required-mark"> *</span></label>
            <textarea
              value={artifactManualCoreVoice}
              onChange={(e) => setArtifactManualCoreVoice(e.target.value)}
              placeholder="How should this sound? e.g., crisp, insightful, slightly witty, no fluff."
            />
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
        <h3 style={{ marginTop: 0 }}>Tone Nuances</h3>
        <p className="note" style={{ marginTop: "4px" }}>Base tone from project: <strong>{projectToneBase}</strong></p>
        <div className="grid two">
          {[
            ["directness", "Directness", "soft", "direct"],
            ["warmth", "Warmth", "neutral", "warm"],
            ["energy", "Energy", "calm", "high-energy"],
            ["authority", "Authority", "exploratory", "decisive"],
          ].map(([key, label, left, right]) => (
            <div key={key}>
              <label>{label}</label>
              <input
                type="range"
                min="0"
                max="4"
                step="1"
                value={Number(artifactToneNuance[key] ?? 2)}
                onChange={(e) => updateArtifactToneNuance(key, Number(e.target.value))}
              />
              <div className="row note" style={{ justifyContent: "space-between" }}>
                <span>{left} &lt;-&gt; {right}</span>
                <span>{artifactToneNuance[key] ?? 2}/4</span>
              </div>
            </div>
          ))}
          {projectToneBase === "analytical" ? (
            <>
              <div>
                <label>Rigor</label>
                <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.rigor ?? 3)} onChange={(e) => updateArtifactToneNuance("rigor", Number(e.target.value))} />
                <div className="row note" style={{ justifyContent: "space-between" }}><span>intuitive &lt;-&gt; evidence-led</span><span>{artifactToneNuance.rigor ?? 3}/4</span></div>
              </div>
              <div>
                <label>Abstraction level</label>
                <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.abstraction ?? 2)} onChange={(e) => updateArtifactToneNuance("abstraction", Number(e.target.value))} />
                <div className="row note" style={{ justifyContent: "space-between" }}><span>tactical &lt;-&gt; strategic</span><span>{artifactToneNuance.abstraction ?? 2}/4</span></div>
              </div>
              <div>
                <label>Framework mode</label>
                <select value={artifactFrameworkMode} onChange={(e) => setArtifactFrameworkMode(e.target.value)}>
                  <option value="none">{formatOptionLabel("none")}</option>
                  <option value="light">{formatOptionLabel("light")}</option>
                  <option value="strong">{formatOptionLabel("strong")}</option>
                </select>
              </div>
            </>
          ) : null}
          {projectToneBase === "professional" ? (
            <>
              <div>
                <label>Formality</label>
                <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.formality ?? 3)} onChange={(e) => updateArtifactToneNuance("formality", Number(e.target.value))} />
                <div className="row note" style={{ justifyContent: "space-between" }}><span>relaxed &lt;-&gt; formal</span><span>{artifactToneNuance.formality ?? 3}/4</span></div>
              </div>
              <div>
                <label>Diplomacy</label>
                <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.diplomacy ?? 3)} onChange={(e) => updateArtifactToneNuance("diplomacy", Number(e.target.value))} />
                <div className="row note" style={{ justifyContent: "space-between" }}><span>blunt &lt;-&gt; tactful</span><span>{artifactToneNuance.diplomacy ?? 3}/4</span></div>
              </div>
            </>
          ) : null}
          {projectToneBase === "conversational" ? (
            <>
              <div>
                <label>Humor</label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="1"
                  value={humorLabelToSlider(artifactToneNuance.humor || "light")}
                  onChange={(e) => updateArtifactToneNuance("humor", humorSliderToLabel(Number(e.target.value)))}
                />
                <div className="row note" style={{ justifyContent: "space-between" }}>
                  <span>none &lt;-&gt; playful</span>
                  <span>{String(artifactToneNuance.humor || "light")}</span>
                </div>
              </div>
              <div>
                <label>Story-ness</label>
                <input type="range" min="0" max="4" step="1" value={Number(artifactToneNuance.storyness ?? 2)} onChange={(e) => updateArtifactToneNuance("storyness", Number(e.target.value))} />
                <div className="row note" style={{ justifyContent: "space-between" }}><span>straightforward &lt;-&gt; story-led</span><span>{artifactToneNuance.storyness ?? 2}/4</span></div>
              </div>
            </>
          ) : null}
        </div>
      </div>

      {artifactSelectedAdvancedFormatCards.length ? (
        <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
          <h3 style={{ marginTop: 0 }}>Format-specific Advanced Settings (optional)</h3>
          {artifactSelectedAdvancedFormatCards.map((card) => {
            const adv = artifactFormatAdvanced?.[card.key] || {};
            const open = !!artifactAdvancedOpen?.[card.key];
            return (
              <div key={`adv-${card.key}`} className="artifact-advanced-block">
                <button
                  type="button"
                  className={`artifact-advanced-toggle ${open ? "artifact-advanced-toggle-open" : ""}`}
                  onClick={() => toggleArtifactAdvancedDrawer(card.key)}
                >
                  <span>
                    <strong>{card.key}</strong>
                    <span className="note" style={{ marginLeft: "8px" }}>{card.description}</span>
                  </span>
                  <span className="note">{open ? "Collapse" : "Expand"}</span>
                </button>
                {open ? (
                  <div className="grid two" style={{ marginTop: "8px" }}>
                    {card.key === "caption" ? (
                      <>
                        <div><label>length</label><select value={adv.length || "short"} onChange={(e) => updateArtifactAdvanced("caption", "length", e.target.value)}><option value="short">{formatOptionLabel("short")}</option><option value="medium">{formatOptionLabel("medium")}</option></select></div>
                        <div><label>emoji_density</label><select value={adv.emoji_density || "light"} onChange={(e) => updateArtifactAdvanced("caption", "emoji_density", e.target.value)}><option value="none">{formatOptionLabel("none")}</option><option value="light">{formatOptionLabel("light")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="high">{formatOptionLabel("high")}</option></select></div>
                        <div><label>structure_hint</label><select value={adv.structure_hint || "plain"} onChange={(e) => updateArtifactAdvanced("caption", "structure_hint", e.target.value)}><option value="plain">{formatOptionLabel("plain")}</option><option value="bullet-ish">{formatOptionLabel("bullet-ish")}</option><option value="mini-story">{formatOptionLabel("mini-story")}</option></select></div>
                      </>
                    ) : null}
                    {card.key === "post" ? (
                      <>
                        <div><label>length</label><select value={adv.length || "medium"} onChange={(e) => updateArtifactAdvanced("post", "length", e.target.value)}><option value="short">{formatOptionLabel("short")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="long">{formatOptionLabel("long")}</option></select></div>
                        <div><label>structure_hint</label><select value={adv.structure_hint || "framework-led"} onChange={(e) => updateArtifactAdvanced("post", "structure_hint", e.target.value)}><option value="framework-led">{formatOptionLabel("framework-led")}</option><option value="story-led">{formatOptionLabel("story-led")}</option><option value="list-led">{formatOptionLabel("list-led")}</option></select></div>
                        <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("post", "cta_strength", e.target.value)}><option value="soft">{formatOptionLabel("soft")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="strong">{formatOptionLabel("strong")}</option></select></div>
                      </>
                    ) : null}
                    {card.key === "newsletter" ? (
                      <>
                        <div><label>sections</label><select value={adv.sections || 4} onChange={(e) => updateArtifactAdvanced("newsletter", "sections", Number(e.target.value))}><option value={3}>3</option><option value={4}>4</option><option value={5}>5</option></select></div>
                        <div><label>takeaway_bullets</label><input type="number" min="3" max="6" value={adv.takeaway_bullets || 4} onChange={(e) => updateArtifactAdvanced("newsletter", "takeaway_bullets", Number(e.target.value))} /></div>
                        <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("newsletter", "cta_strength", e.target.value)}><option value="soft">{formatOptionLabel("soft")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="strong">{formatOptionLabel("strong")}</option></select></div>
                      </>
                    ) : null}
                    {card.key === "blog" ? (
                      <>
                        <div><label>seo_intent</label><select value={adv.seo_intent || "informational"} onChange={(e) => updateArtifactAdvanced("blog", "seo_intent", e.target.value)}><option value="informational">{formatOptionLabel("informational")}</option><option value="how-to">{formatOptionLabel("how-to")}</option><option value="comparison">{formatOptionLabel("comparison")}</option></select></div>
                        <div><label>faq_count</label><input type="number" min="0" max="5" value={adv.faq_count ?? 3} onChange={(e) => updateArtifactAdvanced("blog", "faq_count", Number(e.target.value))} /></div>
                        <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("blog", "cta_strength", e.target.value)}><option value="soft">{formatOptionLabel("soft")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="strong">{formatOptionLabel("strong")}</option></select></div>
                      </>
                    ) : null}
                    {card.key === "script_short" ? (
                      <>
                        <div><label>target_duration_sec</label><select value={adv.target_duration_sec || 30} onChange={(e) => updateArtifactAdvanced("script_short", "target_duration_sec", Number(e.target.value))}><option value={15}>15</option><option value={30}>30</option><option value={45}>45</option><option value={60}>60</option></select></div>
                        <div><label>pacing</label><select value={adv.pacing || "normal"} onChange={(e) => updateArtifactAdvanced("script_short", "pacing", e.target.value)}><option value="slow">{formatOptionLabel("slow")}</option><option value="normal">{formatOptionLabel("normal")}</option><option value="fast">{formatOptionLabel("fast")}</option></select></div>
                        <div><label>cta_strength</label><select value={adv.cta_strength || "medium"} onChange={(e) => updateArtifactAdvanced("script_short", "cta_strength", e.target.value)}><option value="soft">{formatOptionLabel("soft")}</option><option value="medium">{formatOptionLabel("medium")}</option><option value="strong">{formatOptionLabel("strong")}</option></select></div>
                      </>
                    ) : null}
                    {card.key === "cta_variants" ? (
                      <>
                        <div><label>variant_count</label><input type="number" min="7" max="11" value={adv.variant_count || 7} onChange={(e) => updateArtifactAdvanced("cta_variants", "variant_count", Number(e.target.value))} /></div>
                        <div style={{ gridColumn: "1 / -1" }}>
                          <label>angles</label>
                          <div className="row" style={{ marginTop: "6px" }}>
                            {["urgency", "curiosity", "benefit", "social-proof", "low-friction", "question"].map((angle) => (
                              <label key={angle} className="tag">
                                <input
                                  type="checkbox"
                                  checked={Array.isArray(adv.angles) && adv.angles.includes(angle)}
                                  onChange={() => toggleArtifactAdvancedAngle(angle)}
                                  style={{ width: "auto", marginRight: "6px" }}
                                />
                                {angle}
                              </label>
                            ))}
                          </div>
                        </div>
                      </>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </>
  );
}
