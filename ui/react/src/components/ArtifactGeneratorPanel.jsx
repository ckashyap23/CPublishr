import React from "react";
import { FORMAT_ADVANCED_DEFAULTS } from "../lib/appConstants";
import { formatOptionLabel } from "../lib/appUtils";
import ArtifactInlineEditPanel from "./ArtifactInlineEditPanel";
import ArtifactIterateImageStylePanel from "./ArtifactIterateImageStylePanel";
import ArtifactIterateAdvancedSettingsPanel from "./ArtifactIterateAdvancedSettingsPanel";
import ArtifactIterateInstructionPanel from "./ArtifactIterateInstructionPanel";
import ArtifactIterateTextStylePanel from "./ArtifactIterateTextStylePanel";
import ArtifactIterateVideoStylePanel from "./ArtifactIterateVideoStylePanel";
import GenerateArtifactsFormatsStep from "./GenerateArtifactsFormatsStep";
import GenerateArtifactsImageStyleStep from "./GenerateArtifactsImageStyleStep";
import GenerateArtifactsTextStyleStep from "./GenerateArtifactsTextStyleStep";
import GenerateArtifactsVideoStyleStep from "./GenerateArtifactsVideoStyleStep";
import StoredArtifactReadOnly from "./StoredArtifactReadOnly";
import StoredArtifactTabs from "./StoredArtifactTabs";

export default function ArtifactGeneratorPanel(props) {
  const {
    active,
    busy,
    artifactsViewMode,
    setArtifactsViewMode,
    isCheckingStoredArtifacts,
    hasStoredArtifactsForProject,
    onViewStoredArtifacts,
    isStoredArtifactsLoading,
    selectedStoredFormat,
    setSelectedStoredFormat,
    setSelectedStoredArtifactTab,
    storedFormats,
    artifactGenerateStep,
    setArtifactGenerateStep,
    setArtifactSuggestions,
    selectedArtifactFormats,
    fetchAndApplyArtifactSuggestions,
    orderArtifactFormats,
    artifactFormatsByKind,
    artifactFormatMeta,
    storedArtifactCountsByFormat,
    toggleArtifactFormat,
    artifactSelectedFormatCards,
    artifactSelectedKinds,
    artifactStyleKindPanel,
    setArtifactStyleKindPanel,
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
    artifactSuggestionsLoading,
    artifactSuggestions,
    artifactImageStyle,
    updateArtifactImageStyle,
    artifactImageAvoidInput,
    setArtifactImageAvoidInput,
    addArtifactImageAvoidTag,
    removeArtifactImageAvoidTag,
    updateArtifactImageBrandColor,
    artifactVideoStyle,
    updateArtifactVideoStyle,
    artifactVideoAvoidInput,
    setArtifactVideoAvoidInput,
    addArtifactVideoAvoidTag,
    removeArtifactVideoAvoidTag,
    updateArtifactVideoBrandColor,
    canGenerateArtifactsNow,
    onGenerateArtifacts,
    isArtifactGenerating,
    generatedArtifacts,
    selectedArtifactTab,
    setSelectedArtifactTab,
    selectedGeneratedArtifact,
    storedArtifacts,
    filteredStoredArtifacts,
    selectedStoredArtifactTab,
    editingArtifactTitleId,
    editingArtifactTitleValue,
    setEditingArtifactTitleValue,
    saveArtifactTitle,
    cancelEditingArtifactTitle,
    startEditingArtifactTitle,
    selectedStoredArtifact,
    artifactEditMode,
    isArtifactEditActive,
    artifactInlineTextareaRef,
    artifactInlineText,
    setArtifactInlineText,
    autoResizeTextarea,
    isArtifactEditing,
    onSaveInlineArtifactEdit,
    resetArtifactEditPanel,
    artifactIterateInstructionTextareaRef,
    artifactIterateInstruction,
    setArtifactIterateInstruction,
    artifactIterateStyleSource,
    setArtifactIterateStyleSource,
    artifactIterateVoiceProfileId,
    setArtifactIterateVoiceProfileId,
    artifactIterateVoiceStyleTextareaRef,
    artifactIterateManualCoreVoice,
    setArtifactIterateManualCoreVoice,
    artifactIterateToneNuance,
    updateArtifactIterateToneNuance,
    artifactIterateFrameworkMode,
    setArtifactIterateFrameworkMode,
    artifactIterateFormatAdvanced,
    updateArtifactIterateAdvanced,
    artifactIterateImageStyle,
    updateArtifactIterateImageStyle,
    updateArtifactIterateImageBrandColor,
    artifactIterateVideoStyle,
    updateArtifactIterateVideoStyle,
    updateArtifactIterateVideoBrandColor,
    onIterateArtifactEdit,
    startInlineArtifactEdit,
    startIterateArtifactEdit,
  } = props;

  if (!active) return null;

  return (
    <div className="card">
      <h2>Artifact Generator</h2>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
        <div className="row">
          <button className={artifactsViewMode === "stored" ? "primary" : "secondary"} disabled={busy || isCheckingStoredArtifacts || !hasStoredArtifactsForProject} onClick={onViewStoredArtifacts}>
            {isStoredArtifactsLoading ? "Loading Artifacts..." : "View Artifacts"}
          </button>
          <button className={artifactsViewMode === "generate" || artifactsViewMode === "" ? "primary" : "secondary"} disabled={busy} onClick={() => setArtifactsViewMode("generate")}>
            Generate Artifacts
          </button>
        </div>
        {artifactsViewMode === "stored" ? (
          <div className="stored-format-picker">
            <label>Select Stored Format</label>
            <select value={selectedStoredFormat} onChange={(e) => { setSelectedStoredFormat(e.target.value); setSelectedStoredArtifactTab(0); }}>
              <option value="" disabled>Select format</option>
              {storedFormats.map((fmt) => <option key={fmt} value={fmt}>{formatOptionLabel(fmt)}</option>)}
            </select>
          </div>
        ) : <div />}
      </div>
      {artifactsViewMode === "" ? <p className="note">Choose `Generate Artifacts` or `View Artifacts` to load a view.</p> : null}
      {artifactsViewMode === "generate" ? (
        <>
          <div className="row" style={{ marginBottom: "10px" }}>
            <button type="button" className={artifactGenerateStep === "formats" ? "primary" : "secondary"} disabled={busy} onClick={() => { setArtifactGenerateStep("formats"); setArtifactSuggestions(null); }}>
              Formats
            </button>
            <button
              type="button"
              className={artifactGenerateStep === "style" ? "primary" : "secondary"}
              disabled={busy || !selectedArtifactFormats.length}
              onClick={() => {
                if (artifactGenerateStep !== "style") {
                  setArtifactGenerateStep("style");
                  fetchAndApplyArtifactSuggestions(selectedArtifactFormats);
                }
              }}
            >
              Style
            </button>
          </div>

          {artifactGenerateStep === "formats" ? (
            <GenerateArtifactsFormatsStep
              busy={busy}
              selectedArtifactFormats={selectedArtifactFormats}
              setArtifactGenerateStep={setArtifactGenerateStep}
              fetchAndApplyArtifactSuggestions={fetchAndApplyArtifactSuggestions}
              orderArtifactFormats={orderArtifactFormats}
              artifactFormatsByKind={artifactFormatsByKind}
              artifactFormatMeta={artifactFormatMeta}
              storedArtifactCountsByFormat={storedArtifactCountsByFormat}
              toggleArtifactFormat={toggleArtifactFormat}
            />
          ) : null}

          {artifactGenerateStep === "style" ? (
            <>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginTop: "6px" }}>
                <div className="note">Selected formats: {artifactSelectedFormatCards.map((x) => x.key).join(", ") || "(none)"}</div>
              </div>
              {artifactSelectedKinds.length > 1 ? (
                <div className="row artifact-kind-tabs" style={{ marginTop: "8px" }}>
                  {artifactSelectedKinds.map((kind) => (
                    <button key={`artifact-style-kind-${kind}`} type="button" className={artifactStyleKindPanel === kind ? "artifact-kind-tab artifact-kind-tab-active" : "artifact-kind-tab"} disabled={busy} onClick={() => setArtifactStyleKindPanel(kind)}>
                      {kind === "text" ? "Text Style" : (kind === "video" || kind === "gif") ? "Video Style" : `${kind[0].toUpperCase()}${kind.slice(1)} Style`}
                    </button>
                  ))}
                </div>
              ) : null}
              <GenerateArtifactsTextStyleStep
                active={artifactSelectedKinds.includes("text") && artifactStyleKindPanel === "text"}
                projectHasSavedVoiceProfileOption={projectHasSavedVoiceProfileOption}
                artifactStyleSource={artifactStyleSource}
                setArtifactStyleSource={setArtifactStyleSource}
                artifactStyleVoiceProfileId={artifactStyleVoiceProfileId}
                setArtifactStyleVoiceProfileId={setArtifactStyleVoiceProfileId}
                setArtifactStyleVoiceProfileDetail={setArtifactStyleVoiceProfileDetail}
                approvedActiveVoiceProfileOptions={approvedActiveVoiceProfileOptions}
                isArtifactStyleVoiceProfileLoading={isArtifactStyleVoiceProfileLoading}
                artifactSelectedVoiceProfilePreview={artifactSelectedVoiceProfilePreview}
                artifactManualCoreVoice={artifactManualCoreVoice}
                setArtifactManualCoreVoice={setArtifactManualCoreVoice}
                projectToneBase={projectToneBase}
                artifactToneNuance={artifactToneNuance}
                updateArtifactToneNuance={updateArtifactToneNuance}
                artifactFrameworkMode={artifactFrameworkMode}
                setArtifactFrameworkMode={setArtifactFrameworkMode}
                humorLabelToSlider={humorLabelToSlider}
                humorSliderToLabel={humorSliderToLabel}
                artifactSelectedAdvancedFormatCards={artifactSelectedAdvancedFormatCards}
                artifactFormatAdvanced={artifactFormatAdvanced}
                artifactAdvancedOpen={artifactAdvancedOpen}
                toggleArtifactAdvancedDrawer={toggleArtifactAdvancedDrawer}
                updateArtifactAdvanced={updateArtifactAdvanced}
                toggleArtifactAdvancedAngle={toggleArtifactAdvancedAngle}
              />
              <GenerateArtifactsImageStyleStep
                active={artifactSelectedKinds.includes("image") && artifactStyleKindPanel === "image"}
                busy={busy}
                artifactSuggestionsLoading={artifactSuggestionsLoading}
                artifactSuggestions={artifactSuggestions}
                artifactImageStyle={artifactImageStyle}
                updateArtifactImageStyle={updateArtifactImageStyle}
                artifactImageAvoidInput={artifactImageAvoidInput}
                setArtifactImageAvoidInput={setArtifactImageAvoidInput}
                addArtifactImageAvoidTag={addArtifactImageAvoidTag}
                removeArtifactImageAvoidTag={removeArtifactImageAvoidTag}
                updateArtifactImageBrandColor={updateArtifactImageBrandColor}
              />
              <GenerateArtifactsVideoStyleStep
                active={(artifactSelectedKinds.includes("video") && artifactStyleKindPanel === "video") || (artifactSelectedKinds.includes("gif") && artifactStyleKindPanel === "gif")}
                busy={busy}
                artifactSuggestionsLoading={artifactSuggestionsLoading}
                artifactSuggestions={artifactSuggestions}
                artifactVideoStyle={artifactVideoStyle}
                updateArtifactVideoStyle={updateArtifactVideoStyle}
                artifactVideoAvoidInput={artifactVideoAvoidInput}
                setArtifactVideoAvoidInput={setArtifactVideoAvoidInput}
                addArtifactVideoAvoidTag={addArtifactVideoAvoidTag}
                removeArtifactVideoAvoidTag={removeArtifactVideoAvoidTag}
                updateArtifactVideoBrandColor={updateArtifactVideoBrandColor}
              />
              <div className="row" style={{ marginTop: "12px" }}>
                <button className="primary" disabled={busy || !canGenerateArtifactsNow} onClick={onGenerateArtifacts}>
                  {isArtifactGenerating ? "Generating Artifacts..." : "Generate Selected Artifacts"}
                </button>
              </div>
            </>
          ) : null}
        </>
      ) : null}
      {isCheckingStoredArtifacts ? <p className="note" style={{ marginTop: "8px" }}>Checking stored artifacts for this project...</p> : null}
      {artifactsViewMode === "stored" && storedArtifacts.length > 0 ? (
        <>
          <h3 style={{ marginTop: "16px" }}>Stored Artifacts</h3>
          {filteredStoredArtifacts.length > 0 ? (
            <>
              <StoredArtifactTabs
                filteredStoredArtifacts={filteredStoredArtifacts}
                selectedStoredFormat={selectedStoredFormat}
                selectedStoredArtifactTab={selectedStoredArtifactTab}
                editingArtifactTitleId={editingArtifactTitleId}
                editingArtifactTitleValue={editingArtifactTitleValue}
                setEditingArtifactTitleValue={setEditingArtifactTitleValue}
                saveArtifactTitle={saveArtifactTitle}
                cancelEditingArtifactTitle={cancelEditingArtifactTitle}
                startEditingArtifactTitle={startEditingArtifactTitle}
                setSelectedStoredArtifactTab={setSelectedStoredArtifactTab}
              />
              {selectedStoredArtifact ? (
                <>
                  <ArtifactInlineEditPanel
                    active={artifactEditMode === "inline"}
                    artifactInlineTextareaRef={artifactInlineTextareaRef}
                    artifactInlineText={artifactInlineText}
                    setArtifactInlineText={setArtifactInlineText}
                    autoResizeTextarea={autoResizeTextarea}
                    busy={busy}
                    isArtifactEditing={isArtifactEditing}
                    onSaveInlineArtifactEdit={onSaveInlineArtifactEdit}
                    resetArtifactEditPanel={resetArtifactEditPanel}
                  />
                  {artifactEditMode === "iterate" ? (
                    <>
                      <ArtifactIterateInstructionPanel
                        active={artifactEditMode === "iterate"}
                        artifactIterateInstructionTextareaRef={artifactIterateInstructionTextareaRef}
                        artifactIterateInstruction={artifactIterateInstruction}
                        setArtifactIterateInstruction={setArtifactIterateInstruction}
                        autoResizeTextarea={autoResizeTextarea}
                      />
                      {String(selectedStoredArtifact?.kind || "").trim() === "text" ? (
                        <>
                          <ArtifactIterateTextStylePanel
                            active={String(selectedStoredArtifact?.kind || "").trim() === "text"}
                            artifactIterateStyleSource={artifactIterateStyleSource}
                            setArtifactIterateStyleSource={setArtifactIterateStyleSource}
                            artifactIterateVoiceProfileId={artifactIterateVoiceProfileId}
                            setArtifactIterateVoiceProfileId={setArtifactIterateVoiceProfileId}
                            approvedActiveVoiceProfileOptions={approvedActiveVoiceProfileOptions}
                            artifactIterateVoiceStyleTextareaRef={artifactIterateVoiceStyleTextareaRef}
                            artifactIterateManualCoreVoice={artifactIterateManualCoreVoice}
                            setArtifactIterateManualCoreVoice={setArtifactIterateManualCoreVoice}
                            autoResizeTextarea={autoResizeTextarea}
                            artifactIterateToneNuance={artifactIterateToneNuance}
                            updateArtifactIterateToneNuance={updateArtifactIterateToneNuance}
                            projectToneBase={projectToneBase}
                            artifactIterateFrameworkMode={artifactIterateFrameworkMode}
                            setArtifactIterateFrameworkMode={setArtifactIterateFrameworkMode}
                          />
                          <ArtifactIterateAdvancedSettingsPanel
                            active={Object.prototype.hasOwnProperty.call(FORMAT_ADVANCED_DEFAULTS, String(selectedStoredArtifact?.format || ""))}
                            selectedStoredArtifact={selectedStoredArtifact}
                            artifactIterateFormatAdvanced={artifactIterateFormatAdvanced}
                            updateArtifactIterateAdvanced={updateArtifactIterateAdvanced}
                          />
                        </>
                      ) : null}
                      <ArtifactIterateImageStylePanel active={String(selectedStoredArtifact?.kind || "").trim() === "image"} artifactIterateImageStyle={artifactIterateImageStyle} updateArtifactIterateImageStyle={updateArtifactIterateImageStyle} updateArtifactIterateImageBrandColor={updateArtifactIterateImageBrandColor} />
                      <ArtifactIterateVideoStylePanel active={String(selectedStoredArtifact?.kind || "").trim() === "video" || String(selectedStoredArtifact?.kind || "").trim() === "gif"} artifactIterateVideoStyle={artifactIterateVideoStyle} updateArtifactIterateVideoStyle={updateArtifactIterateVideoStyle} updateArtifactIterateVideoBrandColor={updateArtifactIterateVideoBrandColor} />
                      <div className="row" style={{ marginTop: "8px" }}>
                        <button type="button" className="primary" disabled={busy || isArtifactEditing} onClick={onIterateArtifactEdit}>
                          {isArtifactEditing ? "Iterating..." : "Iterate Artifact"}
                        </button>
                        <button type="button" className="secondary" disabled={busy || isArtifactEditing} onClick={resetArtifactEditPanel}>
                          Cancel
                        </button>
                      </div>
                    </>
                  ) : null}
                  {!isArtifactEditActive ? (
                    <StoredArtifactReadOnly artifact={selectedStoredArtifact} busy={busy} isArtifactEditing={isArtifactEditing} artifactEditMode={artifactEditMode} startInlineArtifactEdit={startInlineArtifactEdit} startIterateArtifactEdit={startIterateArtifactEdit} />
                  ) : null}
                </>
              ) : null}
            </>
          ) : (
            <p className="note" style={{ marginTop: "8px" }}>No artifacts for selected format.</p>
          )}
        </>
      ) : null}
    </div>
  );
}
