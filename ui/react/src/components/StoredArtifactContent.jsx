import {
  hashtagListFromArtifact,
  imageSrcFromAsset,
  topicTagListFromArtifact,
  videoSrcFromAsset,
} from "../lib/appUtils";

export default function StoredArtifactContent({ artifact }) {
  if (!artifact) return null;

  const fmt = String(artifact.format || "").trim();
  const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
  const body = typeof payload.body === "string" ? payload.body : "";
  const items = Array.isArray(payload.items) ? payload.items : [];
  const settings = payload?.settings && typeof payload.settings === "object" ? payload.settings : {};
  const hashtags = hashtagListFromArtifact(artifact);
  const topicTags = topicTagListFromArtifact(artifact);
  const assets = Array.isArray(payload.assets) ? payload.assets : [];
  const primaryAsset = assets[0] || null;
  const assetRef = String(primaryAsset?.uri || primaryAsset?.path || "").trim();
  const prompts = Array.isArray(payload.prompts) ? payload.prompts : [];
  const qcPromptRef = (() => {
    const fromSettingsUri = String(
      settings?.qc_prompt_uri || settings?.source_prompt_uri || settings?.prompt_uri || ""
    ).trim();
    if (fromSettingsUri) {
      return fromSettingsUri;
    }
    for (const p of prompts) {
      if (!p || typeof p !== "object") continue;
      const uri = String(p.uri || p.url || "").trim();
      if (uri && uri.toLowerCase().includes("/qc-prompts/")) {
        return uri;
      }
    }
    return null;
  })();
  const assetDetails = assetRef ? `File/URL: ${assetRef}` : null;

  if (["image_generation", "post_image", "thumbnail", "banner", "cover"].includes(fmt)) {
    const imageAsset = assets.find((a) => String(a?.mime_type || "").startsWith("image/")) || assets[0] || null;
    const imageSrc = imageSrcFromAsset(imageAsset);
    return (
      <div className="artifact-render">
        {imageSrc ? (
          <img className="artifact-image-preview" src={imageSrc} alt={artifact.title || "Generated image"} />
        ) : (
          <p className="note">
            Image preview unavailable in browser. URI: <code>{String(imageAsset?.uri || imageAsset?.path || "not available")}</code>
          </p>
        )}
        {imageAsset ? (
          <p className="note">Format: {imageAsset.format || "-"}{imageAsset.path ? ` | Path: ${imageAsset.path}` : ""}</p>
        ) : null}
        {assetDetails ? <p className="note artifact-ps-note">{assetDetails}</p> : null}
      </div>
    );
  }

  if (["gif", "reel", "short_video", "video"].includes(fmt)) {
    const imageLikeAsset =
      assets.find((a) => String(a?.mime_type || "").startsWith("image/")) ||
      assets.find((a) => String(a?.format || "").toLowerCase() === "gif") ||
      null;
    const videoAsset = assets.find((a) => String(a?.mime_type || "").startsWith("video/")) || null;
    const imageSrc = imageSrcFromAsset(imageLikeAsset);
    const videoSrc = videoSrcFromAsset(videoAsset);
    const planItems = items
      .map((item) => ({
        seq: Number(item?.sequence || 0),
        text: String(item?.text || "").trim(),
        guidance: String(item?.guidance || "").trim(),
      }))
      .filter((x) => x.text || x.guidance)
      .sort((a, b) => a.seq - b.seq);

    return (
      <div className="artifact-render">
        {imageSrc ? (
          <img className="artifact-image-preview" src={imageSrc} alt={artifact.title || "Generated GIF"} />
        ) : videoSrc ? (
          <video className="artifact-video-preview" src={videoSrc} controls playsInline preload="metadata" />
        ) : (
          <p className="note">
            Media preview unavailable in browser. URI:{" "}
            <code>{String((videoAsset || imageLikeAsset)?.uri || (videoAsset || imageLikeAsset)?.path || "not available")}</code>
          </p>
        )}

        {planItems.length ? (
          <>
            <p className="note" style={{ marginTop: "10px", marginBottom: "6px" }}>Video plan</p>
            <div className="artifact-doc">
              {planItems.map((item, idx) => (
                <p key={`${item.seq}-${idx}`} className="artifact-script-line">
                  <strong>{item.text || `Step ${idx + 1}`}</strong>
                  {item.guidance ? `: ${item.guidance}` : ""}
                </p>
              ))}
            </div>
          </>
        ) : null}

        {assetDetails ? <p className="note artifact-ps-note">{assetDetails}</p> : null}
      </div>
    );
  }

  if (fmt === "cta_variants") {
    const ctas = items
      .map((item) => ({ text: String(item?.text || "").trim(), seq: Number(item?.sequence || 0) }))
      .filter((x) => x.text)
      .sort((a, b) => a.seq - b.seq);
    return (
      <div className="artifact-render">
        <div className="artifact-cta-grid">
          {ctas.map((cta, idx) => (
            <button key={`${cta.seq}-${idx}`} type="button" className="secondary artifact-cta-button">
              {cta.text}
            </button>
          ))}
        </div>
        {assetDetails ? <p className="note artifact-ps-note">{assetDetails}</p> : null}
      </div>
    );
  }

  if (fmt === "script_short") {
    const beats = items
      .map((item) => ({ text: String(item?.text || "").trim(), seq: Number(item?.sequence || 0) }))
      .filter((x) => x.text)
      .sort((a, b) => a.seq - b.seq);
    const targetDurationSec = Number(settings?.target_duration_sec || 0);
    return (
      <div className="artifact-render">
        {targetDurationSec > 0 ? (
          <p className="note" style={{ marginTop: "-2px", marginBottom: "10px" }}>
            Target duration: {targetDurationSec}s
          </p>
        ) : null}
        <div className="artifact-doc">
          {beats.map((beat, idx) => (
            <p key={`${beat.seq}-${idx}`} className="artifact-script-line">{beat.text}</p>
          ))}
        </div>
        {topicTags.length ? (
          <div className="artifact-hashtags">
            {topicTags.map((tag) => <span key={tag} className="artifact-hashtag">{tag}</span>)}
          </div>
        ) : null}
        {assetDetails ? <p className="note artifact-ps-note">{assetDetails}</p> : null}
      </div>
    );
  }

  if (fmt === "blog" || fmt === "blog_long" || fmt === "newsletter") {
    return (
      <div className="artifact-render">
        <article className="artifact-doc">{body || "No content available."}</article>
        {topicTags.length ? (
          <div className="artifact-hashtags">
            {topicTags.map((tag) => <span key={tag} className="artifact-hashtag">{tag}</span>)}
          </div>
        ) : null}
        {assetDetails ? <p className="note artifact-ps-note">{assetDetails}</p> : null}
      </div>
    );
  }

  if (fmt === "caption" || fmt === "post" || fmt === "x_post" || fmt === "linkedin_post" || fmt === "instagram_caption") {
    const socialTags = hashtags.length ? hashtags : topicTags;
    return (
      <div className="artifact-render">
        <div className="artifact-social">{body || "No content available."}</div>
        {socialTags.length ? (
          <div className="artifact-hashtags">
            {socialTags.map((tag) => <span key={tag} className="artifact-hashtag">{tag}</span>)}
          </div>
        ) : null}
        {assetDetails ? <p className="note artifact-ps-note">{assetDetails}</p> : null}
      </div>
    );
  }

  return (
    <>
      {qcPromptRef ? (
        <p className="note artifact-ps-note">
          QC prompt: <code>{qcPromptRef}</code>
        </p>
      ) : null}
      <pre className="content">{JSON.stringify(artifact, null, 2)}</pre>
    </>
  );
}
