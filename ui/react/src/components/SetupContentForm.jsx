import React from "react";
import LabelWithTooltip from "./LabelWithTooltip";
import { formatOptionLabel } from "../lib/appUtils";

export default function SetupContentForm({
  active,
  busy,
  isCheckingProjectData,
  canGenerateContent,
  onGenerateContent,
  isGenerating,
  canContinueToEditorial,
  setPage,
  nodeAudit,
  form,
  setForm,
  TOPIC_TITLE_SUGGESTION,
  CORE_IDEA_SUGGESTION,
  AUDIENCE_OPTIONS,
  AUDIENCE_FAMILIARITY_OPTIONS,
  DETAIL_LEVEL_OPTIONS,
  TONE_OPTIONS,
  STANCE_OPTIONS,
  PRIMARY_GOAL_OPTIONS,
  DESIRED_ACTION_OPTIONS,
  platformTargets,
  toggleTarget,
  userContentTextareaRef,
  USER_CONTENT_SUGGESTION,
}) {
  if (!active) return null;

  return (
    <div className="card">
      <h2>Generate Content</h2>
      <div className="grid two">
        <div>
          <LabelWithTooltip text="Topic Title" required tooltip="A short headline for your post idea. Keep it simple and specific-this is used to name and organize your content." />
          <input value={form.topic_title} onChange={(e) => setForm({ ...form, topic_title: e.target.value })} placeholder={TOPIC_TITLE_SUGGESTION} />
        </div>
        <div>
          <LabelWithTooltip text="Core Idea" required tooltip="The one-sentence point you want to make. If someone reads only this, they should understand your main message." />
          <input value={form.core_idea} onChange={(e) => setForm({ ...form, core_idea: e.target.value })} placeholder={CORE_IDEA_SUGGESTION} />
        </div>
        <div>
          <LabelWithTooltip text="Target Audience" required tooltip="Who you're writing for. Pick the closest match-this helps choose the right language, examples, and assumptions." />
          <select value={form.target_audience_segment} onChange={(e) => setForm({ ...form, target_audience_segment: e.target.value })}>
            {AUDIENCE_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
          </select>
        </div>
        <div>
          <LabelWithTooltip text="Audience Familiarity" tooltip={"How familiar your audience is with this topic.\nNew: new to the topic\nSomewhat familiar: knows basics\nVery familiar: deep understanding"} />
          <select value={form.audience_familiarity} onChange={(e) => setForm({ ...form, audience_familiarity: e.target.value })}>
            {AUDIENCE_FAMILIARITY_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
          </select>
        </div>
        <div>
          <LabelWithTooltip text="Detail Level" tooltip={"How detailed you want the content.\nQuick take: summary\nPractical: actionable depth\nDeep dive: thorough coverage with nuances"} />
          <select value={form.detail_level} onChange={(e) => setForm({ ...form, detail_level: e.target.value })}>
            {DETAIL_LEVEL_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
          </select>
        </div>
        <div>
          <LabelWithTooltip text="Tone Preference" required tooltip={'The "voice" of the writing-how it should sound. Example: conversational, formal, witty, bold, etc.'} />
          <select value={form.tone_preference} onChange={(e) => setForm({ ...form, tone_preference: e.target.value })}>
            {TONE_OPTIONS.map((x) => <option key={x} value={x}>{formatOptionLabel(x)}</option>)}
          </select>
        </div>
        <div>
          <LabelWithTooltip text="Stance" tooltip={"The point of view you want to take.\nSupportive: agree/advocate\nContrarian: challenge the common view\nBalanced: show both sides and conclude"} />
          <select value={form.stance} onChange={(e) => setForm({ ...form, stance: e.target.value || "balanced" })}>
            {STANCE_OPTIONS.map((x) => <option key={x} value={x}>{formatOptionLabel(x)}</option>)}
          </select>
        </div>
        <div>
          <LabelWithTooltip text="Primary Goal" tooltip="What you want this content to achieve. Example: educate, entertain, promote something, start a discussion, or drive sign-ups." />
          <select value={form.primary_goal} onChange={(e) => setForm({ ...form, primary_goal: e.target.value })}>
            {PRIMARY_GOAL_OPTIONS.map((x) => <option key={x} value={x}>{formatOptionLabel(x)}</option>)}
          </select>
        </div>
        <div>
          <LabelWithTooltip text="Desired Action" tooltip="What you want people to do after reading. Example: comment, share, follow, click a link, DM you, subscribe, or buy." />
          <select value={form.desired_action} onChange={(e) => setForm({ ...form, desired_action: e.target.value })}>
            {DESIRED_ACTION_OPTIONS.map((x) => <option key={x} value={x}>{formatOptionLabel(x)}</option>)}
          </select>
        </div>
        <div style={{ gridColumn: "1 / -1" }}>
          <LabelWithTooltip text="Distribution Targets" tooltip="Where you might publish this. This doesn't change the core idea-just helps us prepare formats that fit those platforms later." />
          <div className="row">
            {platformTargets.map((t) => (
              <label key={t} className="tag">
                <input type="checkbox" checked={form.distribution_targets.includes(t)} onChange={() => toggleTarget(t)} style={{ width: "auto", marginRight: "6px" }} />
                {t}
              </label>
            ))}
          </div>
        </div>
        <div style={{ gridColumn: "1 / -1" }}>
          <LabelWithTooltip text="User Content" tooltip="Any raw notes you already have - bullets, a rough draft, links, or context. The more specific this is, the more accurate the output will be." />
          <textarea
            ref={userContentTextareaRef}
            className="user-content-textarea"
            value={form.user_content || ""}
            onChange={(e) => setForm({ ...form, user_content: e.target.value })}
            placeholder={USER_CONTENT_SUGGESTION}
          />
        </div>
      </div>
      <div className="row" style={{ marginTop: "12px" }}>
        <button type="button" className="primary" disabled={busy || isCheckingProjectData || !canGenerateContent} onClick={onGenerateContent}>
          {isGenerating ? "Generating..." : "Generate Content"}
        </button>
        {canContinueToEditorial ? (
          <button className="secondary" disabled={busy} onClick={() => setPage("editorial")}>
            Continue to Editorial
          </button>
        ) : null}
      </div>
      {(isGenerating || nodeAudit.length > 0) ? (
        <div style={{ marginTop: "14px" }}>
          <h3>Workflow Audit (Node 0-2)</h3>
          <div className="chat">
            {nodeAudit.map((entry, idx) => (
              <div key={`${entry.node}-${idx}`} className="msg">
                <div className="who row" style={{ justifyContent: "space-between" }}>
                  <span>{entry.node}</span>
                  <span className={`audit-status ${entry.status || "running"}`}>{entry.status}</span>
                </div>
                {entry.output ? (
                  <pre className="content" style={{ marginTop: "6px", maxHeight: "220px" }}>
                    {JSON.stringify(entry.output, null, 2)}
                  </pre>
                ) : (
                  <div className="note">Running...</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
