import LabelWithTooltip from "./LabelWithTooltip";

export default function ArtifactIterateInstructionPanel({
  active,
  artifactIterateInstructionTextareaRef,
  artifactIterateInstruction,
  setArtifactIterateInstruction,
  autoResizeTextarea,
}) {
  if (!active) return null;

  return (
    <div className="card" style={{ marginTop: "8px", marginBottom: "8px" }}>
      <LabelWithTooltip
        text="Edit Instruction"
        tooltip="Describe exactly how to modify this artifact."
      />
      <textarea
        ref={artifactIterateInstructionTextareaRef}
        className="artifact-edit-textarea"
        value={artifactIterateInstruction}
        onChange={(e) => {
          setArtifactIterateInstruction(e.target.value);
          autoResizeTextarea(e.target);
        }}
        placeholder="Describe how to modify this artifact..."
      />
    </div>
  );
}
