export default function VoiceProfilesSettings({
  active,
  busy,
  authToken,
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

  return (
    <>
      <div className="card">
        <h2 style={{ marginBottom: 0 }}>Voice Profile Settings</h2>
        {!authToken ? (
          <p className="note">Login first to access voice profile APIs.</p>
        ) : null}
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
          <h3 style={{ margin: 0 }}>Collections</h3>
          {showVpCreateCollectionForm ? (
            <button
              className="secondary"
              disabled={busy || !authToken}
              onClick={() => {
                setShowVpCreateCollectionForm(false);
                setVpCreateForm({ collection_name: "", platforms: ["linkedin"] });
              }}
            >
              Cancel
            </button>
          ) : (
            <button className="secondary" disabled={busy || !authToken} onClick={() => setShowVpCreateCollectionForm(true)}>Create Collection</button>
          )}
        </div>
        {showVpCreateCollectionForm ? (
          <>
            <div className="grid two">
              <div>
                <label>Collection Name</label>
                <input
                  value={vpCreateForm.collection_name}
                  onChange={(e) => setVpCreateForm((prev) => ({ ...prev, collection_name: e.target.value }))}
                />
              </div>
              <div>
                <label>Platforms</label>
                <div className="row">
                  {platformTargets.map((p) => (
                    <label key={`vp-platform-${p}`} className="tag">
                      <input
                        type="checkbox"
                        checked={(vpCreateForm.platforms || []).includes(p)}
                        onChange={() => toggleVpPlatform(p)}
                        style={{ width: "auto", marginRight: "6px" }}
                      />
                      {p}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="row" style={{ marginTop: "10px" }}>
              <button className="primary" disabled={busy || !authToken} onClick={onVpCreateCollection}>Create Collection</button>
            </div>
          </>
        ) : (
          <>
            {vpCollections.length === 0 ? <p className="note">No voice profile collections found.</p> : null}
            <div className="row">
              {vpCollections.map((c) => (
                <button
                  key={c.collection_id}
                  className={vpSelectedCollectionId === c.collection_id ? "primary" : "secondary"}
                  onClick={() => onSelectVpCollection(c.collection_id)}
                >
                  {c.collection_name}
                </button>
              ))}
            </div>
            {vpSelectedCollectionId ? (
              <p className="note" style={{ marginTop: "8px" }}>Selected collection id: {vpSelectedCollectionId}</p>
            ) : null}
          </>
        )}
      </div>

      {vpSelectedCollectionId ? (
        <div className="card">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
            <h3 style={{ margin: 0 }}>Collection Datasets</h3>
          </div>
          <div className="grid two">
            <div className="card" style={{ marginBottom: 0 }}>
              <h3 style={{ marginTop: 0 }}>Upload Dataset</h3>
              <div style={{ marginBottom: "10px" }}>
                <label>Dataset Source</label>
                <select
                  value={vpDatasetSourceMode}
                  onChange={(e) => {
                    const next = String(e.target.value || "azure");
                    setVpDatasetSourceMode(next === "local" ? "local" : "azure");
                    window.localStorage.setItem("cpublishr_vp_dataset_source_mode", next === "local" ? "local" : "azure");
                  }}
                >
                  <option value="azure">Azure Blob Storage</option>
                  <option value="local">Local File Path</option>
                </select>
              </div>
              <div className="grid two">
                <div>
                  <label>Dataset Name</label>
                  <input value={vpDatasetForm.dataset_name} onChange={(e) => setVpDatasetForm((prev) => ({ ...prev, dataset_name: e.target.value }))} />
                </div>
                <div>
                  <label>Source Profile (optional)</label>
                  <input value={vpDatasetForm.source_profile} onChange={(e) => setVpDatasetForm((prev) => ({ ...prev, source_profile: e.target.value }))} />
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <label>{vpDatasetSourceMode === "local" ? "Local File Selection" : "Azure Source Path"}</label>
                  <input
                    value={vpDatasetForm.blob_prefix}
                    onChange={(e) => {
                      const next = e.target.value;
                      setVpDatasetForm((prev) => ({ ...prev, blob_prefix: next }));
                      if (vpDatasetSourceMode === "local") setVpDatasetLocalFiles([]);
                    }}
                    placeholder={
                      vpDatasetSourceMode === "local"
                        ? "Use Browse Local Path to pick one or more files"
                        : "azure://profile-entries/user_id/dataset_name/ OR full blob URL OR container-relative prefix"
                    }
                  />
                  {vpDatasetSourceMode === "local" ? (
                    <div className="row" style={{ marginTop: "8px" }}>
                      <button
                        type="button"
                        className="secondary"
                        disabled={busy || isVpPickingLocalDatasetPath}
                        onClick={() => pickVpDatasetPath("files")}
                      >
                        {isVpPickingLocalDatasetPath ? "Opening..." : "Browse Local Path"}
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
              <div style={{ marginTop: "8px" }}>
                <label>Sample Scope Note (optional)</label>
                <textarea value={vpDatasetForm.sample_scope_note} onChange={(e) => setVpDatasetForm((prev) => ({ ...prev, sample_scope_note: e.target.value }))} />
              </div>
              <p className="note" style={{ marginTop: "8px" }}>
                {vpDatasetSourceMode === "local"
                  ? `Select one or more local files on the backend machine.${vpDatasetLocalFiles.length ? ` ${vpDatasetLocalFiles.length} file(s) selected.` : ""}`
                  : "Use azure://container/prefix, a full Azure blob URL, or a container-relative prefix."}
              </p>
              <div className="row" style={{ marginTop: "10px" }}>
                <button className="primary" disabled={busy || !authToken || !vpSelectedCollectionId} onClick={onVpCreateDataset}>Upload Dataset</button>
              </div>
            </div>

            <div className="card" style={{ marginBottom: 0 }}>
              <h3 style={{ marginTop: 0 }}>Saved Datasets</h3>
              {!vpCollectionDetail?.datasets?.length ? <p className="note">No datasets uploaded yet.</p> : null}
              <div className="row">
                {(vpCollectionDetail?.datasets || []).map((d) => (
                  <span key={d.dataset_id} className="tag">
                    {d.dataset_name} ({d.entry_count || 0})
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {vpSelectedCollectionId ? (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Collection Voice Profiles</h3>
          <div className="card" style={{ marginTop: "12px", marginBottom: 0 }}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
              <h3 style={{ marginTop: 0, marginBottom: 0 }}>Existing Voice Profiles</h3>
              <div className="row">
                <button
                  className="secondary"
                  disabled={busy || !authToken || !vpSelectedCollectionId}
                  onClick={() => {
                    setVpSelectedProfileId("");
                    setVpProfileDetail(null);
                    setVpSelectedVersionId("");
                    setVpVersionDetail(null);
                    setVpProfileForm({ voice_profile_name: "", intended_use: "" });
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
            {!vpCollectionDetail?.voice_profiles?.length ? <p className="note">No voice profiles generated yet.</p> : null}
            <div className="vp-profile-tag-grid">
              {(vpCollectionDetail?.voice_profiles || []).map((p) => (
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
                      setVpProfileForm((prev) => ({ ...prev, voice_profile_name: p.voice_profile_name, intended_use: "" }));
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
                        placeholder="drafting / analysis / coaching"
                      />
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <label>Select Existing Datasets</label>
                      {!vpCollectionDetail?.datasets?.length ? <p className="note">Upload at least one dataset first.</p> : null}
                      <div className="row" style={{ marginTop: "8px" }}>
                        {(vpCollectionDetail?.datasets || []).map((d) => (
                          <label key={d.dataset_id} className="tag">
                            <input
                              type="checkbox"
                              checked={(vpGenerateForm.dataset_ids || []).includes(d.dataset_id)}
                              onChange={() => toggleVpGenerateDataset(d.dataset_id)}
                              style={{ width: "auto", marginRight: "6px" }}
                            />
                            {d.dataset_name} ({d.entry_count || 0})
                          </label>
                        ))}
                      </div>
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
                          setVpProfileForm({ voice_profile_name: "", intended_use: "" });
                          setVpGenerateForm((prev) => ({ ...prev, dataset_ids: [] }));
                          setVpProfileComposerMode("hidden");
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        className="primary"
                        disabled={busy || !authToken || !vpSelectedCollectionId || !(vpGenerateForm.dataset_ids || []).length || !(vpProfileForm.voice_profile_name || "").trim()}
                        onClick={onVpGenerateVersion}
                      >
                        {isVpGenerating ? "Generating Profile Version..." : "Generate Profile Version"}
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
                      <label>Selected Datasets</label>
                      {!vpVersionDetail?.datasets?.length ? <p className="note">No datasets linked to this version.</p> : null}
                      <div className="row" style={{ marginTop: "8px" }}>
                        {(vpVersionDetail?.datasets || []).map((d) => (
                          <span key={d.voice_profile_version_dataset_id} className="tag">
                            {d.dataset_name || d.dataset_id}
                          </span>
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
      ) : null}
    </>
  );
}
