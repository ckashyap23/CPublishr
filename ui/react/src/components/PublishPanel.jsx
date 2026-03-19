import { artifactHasTags, defaultPublishPartForArtifact, formatOptionLabel } from "../lib/appUtils";

export default function PublishPanel({
  active,
  busy,
  publishSelectedPlatform,
  setPublishSelectedPlatform,
  isPublishPlatformsLoading,
  publishPlatforms,
  isPublishArtifactsLoading,
  isPublishFieldSchemaLoading,
  publishFieldSchema,
  publishFieldMappings,
  publishArtifacts,
  publishArtifactsById,
  addPublishSourceRow,
  updatePublishSourceRow,
  removePublishSourceRow,
  formProjectId,
  areRequiredPublishFieldsMapped,
  openSaveToPublishDialog,
  publishSaveMessage,
  showPublishSaveDialog,
  closeSaveToPublishDialog,
  publishSaveUserName,
  setPublishSaveUserName,
  publishSaveOutputPath,
  setPublishSaveOutputPath,
  onSaveToPublish,
}) {
  if (!active) return null;

  return (
    <>
      <div className="card">
        <h2>Publish</h2>
        <div>
          <label>Select Platform</label>
          <select
            value={publishSelectedPlatform}
            onChange={(e) => setPublishSelectedPlatform(e.target.value)}
            disabled={busy || isPublishPlatformsLoading || !publishPlatforms.length}
          >
            <option value="">{isPublishPlatformsLoading ? "Loading platforms..." : "Select platform"}</option>
            {publishPlatforms.map((p) => (
              <option key={p} value={p}>{formatOptionLabel(p)}</option>
            ))}
          </select>
          {isPublishArtifactsLoading ? (
            <p className="note" style={{ marginTop: "6px" }}>Loading artifacts...</p>
          ) : null}
        </div>

        {!publishSelectedPlatform ? (
          <p className="note" style={{ marginTop: "12px" }}>Select a platform to load mapping fields.</p>
        ) : null}
        {publishSelectedPlatform && isPublishFieldSchemaLoading ? (
          <p className="note" style={{ marginTop: "12px" }}>Loading platform field schema...</p>
        ) : null}

        {publishSelectedPlatform && !isPublishFieldSchemaLoading && publishFieldSchema.length > 0 ? (
          <>
            <h3 style={{ marginTop: "16px" }}>Platform Fields</h3>
            <div className="publish-field-list">
              {publishFieldSchema.map((field) => {
                const fieldKey = String(field?.field_key || "").trim();
                const label = String(field?.label || fieldKey || "Field");
                const rows = Array.isArray(publishFieldMappings?.[fieldKey]) ? publishFieldMappings[fieldKey] : [];
                const acceptedFormats = Array.isArray(field?.accepted_artifact_formats)
                  ? field.accepted_artifact_formats.map((x) => String(x || "").trim()).filter(Boolean)
                  : [];
                const filteredArtifactsForField = publishArtifacts.filter((a) => {
                  if (!acceptedFormats.length) return true;
                  return acceptedFormats.includes(String(a?.format || "").trim());
                });

                return (
                  <div key={`publish-field-${fieldKey}`} className="publish-field-card">
                    <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div className="row" style={{ gap: "6px" }}>
                          <h4 style={{ margin: 0 }}>
                            {label}
                            {field?.required ? <span className="publish-required-mark"> *</span> : null}
                          </h4>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="secondary"
                        disabled={busy}
                        onClick={() => addPublishSourceRow(fieldKey)}
                      >
                        Add Source
                      </button>
                    </div>

                    {rows.length === 0 ? (
                      <p className="note" style={{ marginTop: "6px", marginBottom: "2px" }}>No sources mapped yet.</p>
                    ) : null}

                    {rows.map((row, idx) => {
                      const artifact = publishArtifactsById[row.artifact_id] || null;
                      const canIncludeTags = artifactHasTags(artifact);
                      const showIncludeTags = !!row.artifact_id && canIncludeTags && fieldKey !== "cta_variants";
                      return (
                        <div key={row.source_id || `${fieldKey}-${idx}`} className="publish-source-row">
                          <div className="publish-source-compact-row">
                            <div className="publish-source-artifact">
                              <label>Artifact</label>
                              <select
                                className="publish-source-select"
                                value={row.artifact_id || ""}
                                onChange={(e) => {
                                  const artifactId = e.target.value;
                                  const selectedArtifact = publishArtifactsById[artifactId] || null;
                                  updatePublishSourceRow(fieldKey, row.source_id, {
                                    artifact_id: artifactId,
                                    primary_part: defaultPublishPartForArtifact(selectedArtifact),
                                    include_tags: artifactHasTags(selectedArtifact) ? !!row.include_tags : false,
                                  });
                                }}
                              >
                                <option value="">Select artifact</option>
                                {filteredArtifactsForField.map((a) => (
                                  <option key={a.artifact_id} value={a.artifact_id}>
                                    {`${a.title || a.artifact_id} [${formatOptionLabel(a.format)}]`}
                                  </option>
                                ))}
                              </select>
                            </div>
                            {showIncludeTags ? (
                              <div className="publish-source-options">
                                <label className="tag publish-source-tags-toggle" style={{ display: "inline-flex", alignItems: "center", marginBottom: 0 }}>
                                  <input
                                    type="checkbox"
                                    checked={!!row.include_tags}
                                    onChange={(e) => updatePublishSourceRow(fieldKey, row.source_id, { include_tags: !!e.target.checked })}
                                    style={{ width: "auto", marginRight: "6px" }}
                                  />
                                  Include tags
                                </label>
                              </div>
                            ) : <div />}
                            <div className="publish-source-actions">
                              <button
                                type="button"
                                className="secondary publish-delete-button"
                                onClick={() => removePublishSourceRow(fieldKey, row.source_id)}
                                aria-label="Delete source"
                                title="Delete source"
                              >
                                X
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>

            <div className="row" style={{ marginTop: "14px" }}>
              <button
                className="secondary"
                type="button"
                disabled={
                  busy
                  || !String(formProjectId || "").trim()
                  || !publishSelectedPlatform
                  || !areRequiredPublishFieldsMapped
                }
                onClick={openSaveToPublishDialog}
              >
                Save to Publish
              </button>
              <button className="primary" type="button" disabled>
                Publish (Coming Soon)
              </button>
            </div>
            {!areRequiredPublishFieldsMapped ? (
              <p className="note" style={{ marginTop: "6px" }}>Map all required fields before saving.</p>
            ) : null}
            {publishSaveMessage ? <p className="note" style={{ marginTop: "8px" }}>{publishSaveMessage}</p> : null}
          </>
        ) : null}
      </div>

      {showPublishSaveDialog ? (
        <div className="modal-overlay" onClick={closeSaveToPublishDialog}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>Save To Publish</h3>
            <div>
              <label>Name</label>
              <input
                value={publishSaveUserName}
                onChange={(e) => setPublishSaveUserName(e.target.value)}
                placeholder="Enter bundle name"
              />
            </div>

            <div style={{ marginTop: "10px" }}>
              <label>Enter Remote Path <span style={{ fontWeight: 400, color: "#8899aa" }}>(optional)</span></label>
              <input
                value={publishSaveOutputPath}
                onChange={(e) => {
                  const next = e.target.value;
                  setPublishSaveOutputPath(next);
                  window.localStorage.setItem("cpublishr_publish_output_path", next);
                }}
                placeholder="azure://container/prefix OR gs://bucket/prefix"
              />
              <p className="note" style={{ marginTop: "6px" }}>
                {/^(azure|az|gs):\/\//i.test(String(publishSaveOutputPath || "").trim())
                  ? "ZIP will be saved to the remote path above."
                  : "ZIP will be downloaded to your device."}
              </p>
            </div>

            <div className="row" style={{ marginTop: "14px", justifyContent: "flex-end" }}>
              <button type="button" className="secondary" onClick={closeSaveToPublishDialog} disabled={busy}>
                Cancel
              </button>
              <button type="button" className="primary" onClick={onSaveToPublish} disabled={busy}>
                {busy ? "Downloading..." : "Download"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
