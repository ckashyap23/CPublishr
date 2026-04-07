export default function VoiceProfilesSettings({
  active,
  busy,
  authToken,
  defaultVoiceProfileDetail,
  vpProfilesIndex,
  showVpCreateCollectionForm,
  setShowVpCreateCollectionForm,
  vpCreateForm,
  setVpCreateForm,
  platformTargets,
  toggleVpPlatform,
  onVpCreateCollection,
  vpCollections,
  vpSelectedCollectionId,
  onSelectVpCollection,
  vpDatasetSourceMode,
  setVpDatasetSourceMode,
  vpDatasetForm,
  setVpDatasetForm,
  vpDatasetLocalFiles,
  setVpDatasetLocalFiles,
  isVpPickingLocalDatasetPath,
  pickVpDatasetPath,
  onVpCreateDataset,
  onVpCreateProfile,
  vpCollectionDetail,
  hasSelectedActiveVoiceProfiles,
  hasSelectedInactiveVoiceProfiles,
  vpCheckedProfileIds,
  updateVpProfilesEnabled,
  deleteVpProfiles,
  vpSelectedProfileId,
  vpProfileComposerMode,
  setVpSelectedProfileId,
  setVpProfileDetail,
  setVpSelectedVersionId,
  setVpVersionDetail,
  vpProfileForm,
  setVpProfileForm,
  vpGenerateForm,
  setVpGenerateForm,
  setVpProfileComposerMode,
  toggleVpCheckedProfile,
  vpSelectedProfileSummary,
  vpProfileDetail,
  toggleVpGenerateDataset,
  isVpGenerating,
  onVpGenerateVersion,
  vpVersionDetail,
  vpSelectedVersionId,
  vpStatusInput,
  setVpStatusInput,
  onVpActivateVersion,
  onVpUpdateStatus,
}) {
  if (!active) return null;

  const profileList = Array.isArray(vpProfilesIndex) ? vpProfilesIndex : [];
  const versionSummary = vpVersionDetail?.style_summary?.summary || "Not specified";
  const versionDoRules = Array.isArray(vpVersionDetail?.do_rules) ? vpVersionDetail.do_rules : [];
  const versionDontRules = Array.isArray(vpVersionDetail?.dont_rules) ? vpVersionDetail.dont_rules : [];

  return (
    <>
      <div className="card">
        <h2 style={{ marginBottom: 0 }}>Voice Profile Settings</h2>
        {!authToken ? (
          <p className="note">Login first to access voice profile APIs.</p>
        ) : null}
      </div>

      {defaultVoiceProfileDetail ? (
        <div className="card">
          <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
            <div>
              <h3 style={{ margin: 0 }}>{defaultVoiceProfileDetail.voice_profile_name}</h3>
              <p className="note" style={{ marginTop: "6px" }}>
                Built-in fallback profile used when no saved voice profile is selected.
              </p>
            </div>
            <span className="vp-profile-status-pill vp-profile-status-pill-success">Built-in</span>
          </div>
          <div style={{ marginBottom: "10px" }}>
            <label>Intended Use</label>
            <div className="row" style={{ marginTop: "8px" }}>
              {(defaultVoiceProfileDetail.intended_uses || []).map((use) => (
                <span key={use} className="tag">{use}</span>
              ))}
            </div>
          </div>
          <div style={{ marginBottom: "10px" }}>
            <label>Core Voice</label>
            <div className="note" style={{ marginTop: "6px", fontSize: "14px" }}>
              {defaultVoiceProfileDetail.core_voice}
            </div>
          </div>
          <div style={{ marginBottom: "10px" }}>
            <label>Summary</label>
            <div className="note" style={{ marginTop: "6px", fontSize: "14px" }}>
              {defaultVoiceProfileDetail.summary}
            </div>
          </div>
          <div style={{ marginBottom: "10px" }}>
            <label>Do Rules</label>
            <div className="row" style={{ marginTop: "8px" }}>
              {(defaultVoiceProfileDetail.do_rules || []).map((rule) => (
                <span key={rule} className="tag">{rule}</span>
              ))}
            </div>
          </div>
          <div>
            <label>Don't Rules</label>
            <div className="row" style={{ marginTop: "8px" }}>
              {(defaultVoiceProfileDetail.dont_rules || []).map((rule) => (
                <span key={rule} className="tag">{rule}</span>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Saved Voice Profiles</h3>
          <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
              <h3 style={{ marginTop: 0, marginBottom: 0 }}>Existing Voice Profiles</h3>
              <div className="row">
                <button
                  className="secondary"
                  disabled={busy || !authToken}
                  onClick={() => {
                    setVpSelectedProfileId("");
                    setVpProfileDetail(null);
                    setVpSelectedVersionId("");
                    setVpVersionDetail(null);
                    setVpProfileForm({
                      voice_profile_name: "",
                      intended_use: "",
                      core_voice: "",
                      summary: "",
                      do_rules_text: "",
                      dont_rules_text: "",
                    });
                    setVpGenerateForm((prev) => ({ ...prev, dataset_ids: [] }));
                    setVpProfileComposerMode("create");
                  }}
                >
                  Create Profile
                </button>
                {hasSelectedActiveVoiceProfiles ? (
                  <button className="secondary" disabled={busy} onClick={() => updateVpProfilesEnabled(false)}>
                    Deactivate
                  </button>
                ) : null}
                {hasSelectedInactiveVoiceProfiles ? (
                  <button className="secondary" disabled={busy} onClick={() => updateVpProfilesEnabled(true)}>
                    Activate
                  </button>
                ) : null}
                {vpCheckedProfileIds.length ? (
                  <button className="danger" disabled={busy} onClick={deleteVpProfiles}>
                    Delete
                  </button>
                ) : null}
              </div>
            </div>
            {!profileList.length ? <p className="note">No saved voice profiles yet.</p> : null}
            <div className="vp-profile-tag-grid">
              {profileList.map((p) => (
                <div
                  key={p.voice_profile_id}
                  className={[
                    "vp-profile-tag-card",
                    vpSelectedProfileId === p.voice_profile_id && vpProfileComposerMode === "existing" ? "vp-profile-tag-card-selected" : "",
                    p.is_enabled === false ? "vp-profile-tag-disabled" : "",
                  ].filter(Boolean).join(" ")}
                >
                  <input
                    type="checkbox"
                    className="vp-profile-tag-checkbox"
                    checked={vpCheckedProfileIds.includes(p.voice_profile_id)}
                    onChange={() => toggleVpCheckedProfile(p.voice_profile_id)}
                  />
                  <button
                    type="button"
                    className="vp-profile-tag-button"
                    onClick={() => {
                      setVpSelectedProfileId(p.voice_profile_id);
                      setVpProfileForm({
                        voice_profile_name: p.voice_profile_name,
                        intended_use: vpVersionDetail?.version?.intended_use || "",
                        core_voice: vpVersionDetail?.version?.core_voice || "",
                        summary: vpVersionDetail?.style_summary?.summary || "",
                        do_rules_text: Array.isArray(vpVersionDetail?.do_rules) ? vpVersionDetail.do_rules.join("\n") : "",
                        dont_rules_text: Array.isArray(vpVersionDetail?.dont_rules) ? vpVersionDetail.dont_rules.join("\n") : "",
                      });
                      setVpGenerateForm((prev) => ({ ...prev, dataset_ids: [] }));
                      setVpProfileComposerMode("existing");
                    }}
                  >
                    <span>{p.voice_profile_name}</span>
                    {p.is_enabled === false ? <span className="vp-profile-status-pill vp-profile-status-pill-danger">Deactivated</span> : null}
                  </button>
                </div>
              ))}
            </div>
            {vpProfileComposerMode !== "hidden" ? (
              <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
                {vpProfileComposerMode === "create" ? (
                  <div>
                    <h3 style={{ marginTop: 0 }}>Create Voice Profile</h3>
                    <label>Voice Profile Name</label>
                    <input
                      value={vpProfileForm.voice_profile_name}
                      onChange={(e) => setVpProfileForm((prev) => ({ ...prev, voice_profile_name: e.target.value }))}
                      placeholder="e.g. My Professional Voice"
                    />
                  </div>
                ) : (
                  <div>
                    <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <label>Voice Profile</label>
                        <div className="note" style={{ marginTop: "6px", fontSize: "14px" }}>
                          {vpSelectedProfileSummary?.voice_profile_name || vpProfileForm.voice_profile_name || "(unnamed)"}
                        </div>
                      </div>
                      <div className="row" style={{ gap: "8px" }}>
                        {vpSelectedProfileSummary?.is_enabled === false ? (
                          <span className="vp-profile-status-pill vp-profile-status-pill-danger">Deactivated</span>
                        ) : null}
                        {vpProfileDetail?.voice_profile?.active_version?.version_no ? (
                          <span className="vp-profile-status-pill vp-profile-status-pill-success">
                            Active v{vpProfileDetail.voice_profile.active_version.version_no}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                )}
                {vpProfileComposerMode === "create" ? (
                  <>
                    <div style={{ marginTop: "12px" }}>
                      <label>Intended Use</label>
                      <input
                        value={vpProfileForm.intended_use}
                        onChange={(e) => setVpProfileForm((prev) => ({ ...prev, intended_use: e.target.value }))}
                        placeholder="Optional"
                      />
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Core Voice</label>
                      <textarea
                        value={vpProfileForm.core_voice}
                        onChange={(e) => setVpProfileForm((prev) => ({ ...prev, core_voice: e.target.value }))}
                        placeholder="Describe the voice in a short phrase or sentence"
                      />
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Summary</label>
                      <textarea
                        value={vpProfileForm.summary}
                        onChange={(e) => setVpProfileForm((prev) => ({ ...prev, summary: e.target.value }))}
                        placeholder="High-level summary of how this voice should sound"
                      />
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Dos</label>
                      <textarea
                        value={vpProfileForm.do_rules_text}
                        onChange={(e) => setVpProfileForm((prev) => ({ ...prev, do_rules_text: e.target.value }))}
                        placeholder="One rule per line"
                      />
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Don'ts</label>
                      <textarea
                        value={vpProfileForm.dont_rules_text}
                        onChange={(e) => setVpProfileForm((prev) => ({ ...prev, dont_rules_text: e.target.value }))}
                        placeholder="One rule per line"
                      />
                    </div>
                    <div className="row" style={{ marginTop: "12px" }}>
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() => {
                          setVpSelectedProfileId("");
                          setVpProfileDetail(null);
                          setVpSelectedVersionId("");
                          setVpVersionDetail(null);
                          setVpProfileForm({
                            voice_profile_name: "",
                            intended_use: "",
                            core_voice: "",
                            summary: "",
                            do_rules_text: "",
                            dont_rules_text: "",
                          });
                          setVpGenerateForm((prev) => ({ ...prev, dataset_ids: [] }));
                          setVpProfileComposerMode("hidden");
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        className="secondary"
                        disabled={busy || !authToken || !(vpProfileForm.voice_profile_name || "").trim()}
                        onClick={onVpCreateProfile}
                      >
                        Save Profile
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{ marginTop: "12px" }}>
                      <label>Intended Use</label>
                      <div className="note" style={{ marginTop: "6px", fontSize: "14px" }}>
                        {vpVersionDetail?.version?.intended_use || "Not specified"}
                      </div>
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Core Voice</label>
                      <div className="note" style={{ marginTop: "6px", fontSize: "14px" }}>
                        {vpVersionDetail?.version?.core_voice || "Not specified"}
                      </div>
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Summary</label>
                      <div className="note" style={{ marginTop: "6px", fontSize: "14px", whiteSpace: "pre-wrap" }}>
                        {versionSummary}
                      </div>
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Dos</label>
                      {!versionDoRules.length ? <p className="note">No do rules added.</p> : null}
                      <div className="row" style={{ marginTop: "8px" }}>
                        {versionDoRules.map((rule) => (
                          <span key={rule} className="tag">{rule}</span>
                        ))}
                      </div>
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Don'ts</label>
                      {!versionDontRules.length ? <p className="note">No don't rules added.</p> : null}
                      <div className="row" style={{ marginTop: "8px" }}>
                        {versionDontRules.map((rule) => (
                          <span key={rule} className="tag">{rule}</span>
                        ))}
                      </div>
                    </div>
                  </>
                )}
                {isVpGenerating ? (
                  <div style={{ marginTop: "10px" }}>
                    <div className="progress-label">Generating voice profile version...</div>
                    <div className="progress-track">
                      <div className="progress-fill indeterminate" style={{ width: "35%" }} />
                    </div>
                  </div>
                ) : null}
                {vpProfileComposerMode === "existing" ? (
                  <div style={{ marginTop: "14px" }}>
                    <h3 style={{ marginTop: 0, marginBottom: "10px" }}>Versions</h3>
                    {!vpProfileDetail?.versions?.length ? <p className="note">No versions generated yet for this profile.</p> : null}
                    <div className="vp-version-chip-row">
                      {(vpProfileDetail?.versions || []).map((v) => (
                        <button
                          key={v.voice_profile_version_id}
                          className={[
                            "vp-version-chip",
                            vpSelectedVersionId === v.voice_profile_version_id ? "vp-version-chip-selected" : "",
                            v.is_active ? "vp-version-chip-active" : "",
                          ].filter(Boolean).join(" ")}
                          onClick={() => setVpSelectedVersionId(v.voice_profile_version_id)}
                        >
                          <span>v{v.version_no}</span>
                        </button>
                      ))}
                    </div>
                    {vpProfileDetail?.versions?.length ? (
                      <div className="row" style={{ marginTop: "10px" }}>
                        {!vpVersionDetail?.version?.is_active ? (
                          <button className="primary" disabled={busy || !authToken || !vpSelectedVersionId} onClick={onVpActivateVersion}>Activate</button>
                        ) : null}
                        <input
                          style={{ maxWidth: "240px" }}
                          value={vpStatusInput}
                          onChange={(e) => setVpStatusInput(e.target.value)}
                          placeholder="approved / rejected / generated"
                        />
                        <button className="secondary" disabled={busy || !authToken || !vpSelectedVersionId} onClick={onVpUpdateStatus}>Update Status</button>
                      </div>
                    ) : null}
                    {vpVersionDetail ? (
                      <>
                        <h3 style={{ marginTop: "14px" }}>Version Detail</h3>
                        <pre className="content">{JSON.stringify(vpVersionDetail, null, 2)}</pre>
                      </>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
      </div>
    </>
  );
}
