export default function LabelWithTooltip({ text, tooltip, required = false }) {
  return (
    <div className="label-row">
      <label>
        {text}
        {required ? <span className="publish-required-mark"> *</span> : null}
      </label>
      {tooltip ? (
        <button
          type="button"
          className="tooltip-icon"
          title={tooltip}
          aria-label={tooltip}
          onClick={() => {}}
        >
          ?
        </button>
      ) : null}
    </div>
  );
}
