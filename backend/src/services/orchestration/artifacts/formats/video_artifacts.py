# video_generation.py
from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from src.core.config import settings
from src.services.orchestration.artifact_schema import default_payload_template
from src.services.orchestration.artifacts.contracts import ArtifactDraft, PipelineContext
from src.services.orchestration.artifacts.persistence import (
    save_video_bytes_to_local,
    upload_artifact_bytes,
    video_output_dir,
)

logger = logging.getLogger(__name__)

# Supported builder formats (UI-facing)
VIDEO_FORMATS = {"gif", "reel", "short_video"}


# =============================================================================
# Azure Sora 1 (Preview) API
# =============================================================================


@dataclass(frozen=True)
class AzureSoraPreviewConfig:
    endpoint: str
    api_key: str
    api_version: str  # typically "preview"


def _get_azure_sora_preview_config() -> AzureSoraPreviewConfig | None:
    endpoint = (settings.azure_video_endpoint or "").strip().rstrip("/")
    api_key = (settings.azure_api_key or "").strip()
    api_version = (settings.azure_video_api_version or "").strip() or "preview"
    if not endpoint or not api_key:
        return None
    return AzureSoraPreviewConfig(endpoint=endpoint, api_key=api_key, api_version=api_version)


def _sora_headers(cfg: AzureSoraPreviewConfig) -> dict[str, str]:
    return {"api-key": cfg.api_key, "Content-Type": "application/json"}


def _sora_create_job(
    *,
    cfg: AzureSoraPreviewConfig,
    deployment_name: str,
    prompt: str,
    width: int,
    height: int,
    n_seconds: int,
    n_variants: int = 1,
    timeout_s: float = 60.0,
) -> tuple[str | None, str | None]:
    """
    Sora 1 preview: create job
      POST {endpoint}/openai/v1/video/generations/jobs?api-version=preview
      body: {prompt,width,height,n_seconds,model,n_variants}
    """
    url = f"{cfg.endpoint}/openai/v1/video/generations/jobs?api-version={cfg.api_version}"
    body: dict[str, Any] = {
        "prompt": (prompt or "")[:32000],
        "width": int(width),
        "height": int(height),
        "n_seconds": int(n_seconds),
        "model": deployment_name,
        "n_variants": int(max(1, min(4, n_variants))),
    }

    try:
        logger.info("Azure Sora create job: endpoint=%s deployment=%s", cfg.endpoint, deployment_name)
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(url, headers=_sora_headers(cfg), json=body)
            resp.raise_for_status()
            job_id = str(resp.json().get("id") or "").strip()
            if not job_id:
                return None, "Azure Sora create returned no job id."
            return job_id, None
    except httpx.HTTPStatusError as e:
        detail = (e.response.text or "").strip()
        msg = f"Azure Sora create HTTP {e.response.status_code}"
        if detail:
            msg = f"{msg}: {detail[:800]}"
        logger.error("Azure Sora create failed: endpoint=%s deployment=%s error=%s", cfg.endpoint, deployment_name, msg)
        return None, msg
    except Exception as e:
        logger.error(
            "Azure Sora create exception: endpoint=%s deployment=%s error=%s",
            cfg.endpoint,
            deployment_name,
            str(e),
        )
        return None, str(e)


def _sora_get_job(
    *,
    cfg: AzureSoraPreviewConfig,
    job_id: str,
    timeout_s: float = 30.0,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Sora 1 preview: job status
      GET {endpoint}/openai/v1/video/generations/jobs/{job_id}?api-version=preview
    """
    url = f"{cfg.endpoint}/openai/v1/video/generations/jobs/{job_id}?api-version={cfg.api_version}"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.get(url, headers={"api-key": cfg.api_key})
            resp.raise_for_status()
            return resp.json(), None
    except httpx.HTTPStatusError as e:
        detail = (e.response.text or "").strip()
        msg = f"Azure Sora status HTTP {e.response.status_code}"
        if detail:
            msg = f"{msg}: {detail[:800]}"
        return None, msg
    except Exception as e:
        return None, str(e)


def _sora_poll_job(
    *,
    cfg: AzureSoraPreviewConfig,
    job_id: str,
    max_wait_seconds: int = 900,
    poll_interval_seconds: int = 5,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Poll job until status in (succeeded|failed|cancelled) or timeout.
    """
    start = time.time()
    last_err: str | None = None

    while True:
        payload, err = _sora_get_job(cfg=cfg, job_id=job_id, timeout_s=30.0)
        if err:
            last_err = err
        if payload:
            status = str(payload.get("status") or "").lower()
            if status in {"succeeded", "failed", "cancelled"}:
                return payload, None

        if (time.time() - start) >= max_wait_seconds:
            return None, f"Timed out waiting for Sora job {job_id}. Last error: {last_err}"

        time.sleep(max(2, poll_interval_seconds))


def _sora_download_video(
    *,
    cfg: AzureSoraPreviewConfig,
    generation_id: str,
    timeout_s: float = 180.0,
) -> tuple[bytes | None, str | None]:
    """
    Sora 1 preview: download MP4 bytes
      GET {endpoint}/openai/v1/video/generations/{generation_id}/content/video?api-version=preview
    """
    url = f"{cfg.endpoint}/openai/v1/video/generations/{generation_id}/content/video?api-version={cfg.api_version}"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.get(url, headers={"api-key": cfg.api_key})
            resp.raise_for_status()
            return resp.content, None
    except httpx.HTTPStatusError as e:
        detail = (e.response.text or "").strip()
        msg = f"Azure Sora download HTTP {e.response.status_code}"
        if detail:
            msg = f"{msg}: {detail[:800]}"
        return None, msg
    except Exception as e:
        return None, str(e)


# =============================================================================
# FFMPEG stitcher + GIF exporter (best-effort)
# =============================================================================


def _ffmpeg_bin() -> str:
    """Return the ffmpeg executable path. Reads FFMPEG_PATH env var, falls back to 'ffmpeg' on PATH."""
    return os.environ.get("FFMPEG_PATH", "").strip() or "ffmpeg"


def _ffmpeg_exists() -> bool:
    try:
        subprocess.run([_ffmpeg_bin(), "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception:
        return False


def _run_ffmpeg(cmd: list[str]) -> tuple[bool, str | None]:
    # Replace bare "ffmpeg" at position 0 with the resolved binary path
    if cmd and cmd[0] == "ffmpeg":
        cmd = [_ffmpeg_bin()] + cmd[1:]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            return False, err[:2000] if err else "ffmpeg failed with non-zero exit code."
        return True, None
    except Exception as e:
        return False, str(e)


def _concat_mp4(clips: list[Path], *, out_path: Path) -> tuple[Path | None, str | None]:
    """
    Concatenate MP4 clips using ffmpeg concat demuxer.
    Requires all clips to exist locally.
    """
    if not clips:
        return None, "No clips provided for stitching."
    if not _ffmpeg_exists():
        return None, "ffmpeg not found on PATH; cannot stitch clips."

    for p in clips:
        if not p.exists():
            return None, f"Missing clip on disk: {p}"

    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
            for p in clips:
                ap = str(p.resolve()).replace("'", r"'\''")
                f.write(f"file '{ap}'\n")
            list_path = Path(f.name)

        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(out_path)]
        ok, err = _run_ffmpeg(cmd)
        try:
            list_path.unlink(missing_ok=True)
        except Exception:
            pass
        if not ok:
            return None, err
        return out_path, None
    except Exception as e:
        return None, str(e)


def _mp4_to_gif(
    *,
    mp4_path: Path,
    gif_path: Path,
    fps: int = 12,
    width: int | None = 720,
) -> tuple[Path | None, str | None]:
    """
    Convert MP4 -> GIF using palettegen/paletteuse for reasonable quality.
    """
    if not _ffmpeg_exists():
        return None, "ffmpeg not found on PATH; cannot convert mp4 to gif."
    if not mp4_path.exists():
        return None, f"Missing input mp4 for gif conversion: {mp4_path}"

    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".png") as pal:
            palette_path = Path(pal.name)

        scale_part = f"scale={width}:-1:flags=lanczos" if width else "scale=iw:ih"
        vf_base = f"fps={int(fps)},{scale_part}"

        cmd1 = ["ffmpeg", "-y", "-i", str(mp4_path), "-vf", f"{vf_base},palettegen", str(palette_path)]
        ok1, err1 = _run_ffmpeg(cmd1)
        if not ok1:
            try:
                palette_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None, err1

        cmd2 = [
            "ffmpeg",
            "-y",
            "-i",
            str(mp4_path),
            "-i",
            str(palette_path),
            "-lavfi",
            f"{vf_base} [x]; [x][1:v] paletteuse",
            str(gif_path),
        ]
        ok2, err2 = _run_ffmpeg(cmd2)

        try:
            palette_path.unlink(missing_ok=True)
        except Exception:
            pass

        if not ok2:
            return None, err2
        return gif_path, None
    except Exception as e:
        return None, str(e)


# =============================================================================
# Format recipes (strict composition defaults injected into prompt)
# =============================================================================


@dataclass(frozen=True)
class VideoRecipe:
    n_seconds: int
    clip_count: int

    # resolution by output_fidelity (must be Sora supported)
    standard_wh: tuple[int, int]
    pro_wh: tuple[int, int]

    export_format: str  # "mp4" or "gif" (gif created via ffmpeg conversion)
    fps_target: int

    prompt_hint: str
    composition_defaults: dict[str, Any]


# =============================================================================
# Enum label expansions (raw dropdown value → descriptive phrase for prompt)
# Unknown/custom values pass through unchanged.
# =============================================================================

_VIDEO_ENUM_EXPANSIONS: dict[str, dict[str, str]] = {
    "mood": {
        "playful": "playful, light, and fun",
        "serious": "serious and authoritative",
        "premium": "premium, sophisticated, luxury feel",
        "cozy": "warm, cozy, and inviting",
        "dramatic": "dramatic, high-contrast, intense",
        "energetic": "energetic and dynamic",
        "inspiring": "uplifting and inspiring",
        "suspenseful": "tense and suspenseful with building tension",
        "mysterious": "mysterious and enigmatic",
        "whimsical": "whimsical and dreamy",
        "futuristic": "sleek futuristic aesthetic",
        "nostalgic": "nostalgic, warm vintage feel",
    },
    "lighting": {
        "soft_daylight": "soft natural daylight",
        "golden_hour": "warm golden hour lighting",
        "sunset_warm": "warm sunset glow",
        "overcast_diffused": "overcast diffused ambient light",
        "studio_softbox": "studio softbox lighting",
        "high_key_bright": "high-key bright even lighting",
        "low_key_moody": "low-key moody shadows",
        "neon_night": "neon-lit nighttime atmosphere",
        "backlit_silhouette": "backlit subject creating silhouette effect",
        "rim_light": "rim/edge lighting separating subject from background",
        "volumetric_godrays": "volumetric god rays filtering through atmosphere",
        "dramatic_spotlight": "dramatic hard spotlight",
    },
    "palette_mode": {
        "brand": "brand color palette (see brand colors below)",
        "monochrome": "monochromatic single-tone palette",
        "pastel": "soft pastel tones, low saturation",
        "neon": "vivid neon colors, high saturation",
        "earthy": "earthy organic tones, warm browns and greens",
        "muted": "muted desaturated tones, soft contrast",
        "high_contrast": "high contrast colors, strong separation",
    },
    "output_fidelity": {
        "standard": "clean and polished, suitable for social media",
        "pro": "cinematic, high production value, detail-rich textures",
    },
    "camera_motion": {
        "slow_dolly_in": "slow dolly-in toward subject",
        "orbital_drift": "slow orbital drift around subject",
        "tracking_follow": "tracking follow shot",
        "static_locked": "static locked-off shot, no camera movement",
        "handheld_documentary": "handheld documentary-style movement",
        "push_pull_oscillate": "slow oscillating push-pull (zoom in and out)",
    },
    "energy_level": {
        "low": "calm and deliberate",
        "medium": "balanced and steady",
        "high": "energetic and fast-paced",
    },
}


def _expand_video_enum(field: str, value: str) -> str:
    """Return the expanded descriptive phrase for a known enum value, or the raw value if unknown."""
    return _VIDEO_ENUM_EXPANSIONS.get(field, {}).get(value, value)


# Maps user energy_level to pacing + motion_intensity overrides for composition_defaults
_VIDEO_ENERGY_LEVEL_MAP: dict[str, tuple[str, str]] = {
    "low": ("slow", "low"),
    "medium": ("medium", "medium"),
    "high": ("fast", "high"),
}


# Narrative roles for short_video segments (injected per-clip into _build_segments)
_SHORT_VIDEO_SEGMENT_ROLES: dict[int, str] = {
    1: "Establishing shot — introduce the subject, setting, and visual identity. Use wide or medium framing.",
    2: "Development 1 — closer engagement with the subject; reveal a detail or show progression.",
    3: "Development 2 — continue progression from a different angle or action phase.",
    4: "Development 3 — peak action or highest engagement moment of the scene.",
    5: "Resolution/Outro — pull back or show a concluding moment; provide visual closure.",
}

VIDEO_RECIPES: dict[str, VideoRecipe] = {
    "gif": VideoRecipe(
        n_seconds=4,
        clip_count=1,
        standard_wh=(720, 720),
        pro_wh=(1080, 1080),
        export_format="gif",
        fps_target=12,
        prompt_hint=(
            "animated GIF loop (4 seconds, seamless); end frame identical to start frame; "
            "prefer subtle oscillating motion (slow zoom bloom, push-pull, parallax layer shift) "
            "over large linear displacement; bold flat tones preferred — avoid heavy cinematic "
            "gradients and soft bokeh which degrade in 256-color GIF palette"
        ),
        composition_defaults={
            "pacing": "medium",
            "motion_intensity": "medium",
            "camera_motion": "subtle_oscillating_loop",
            "overlay": "none",
            "negative_space": "low",
        },
    ),
    "reel": VideoRecipe(
        n_seconds=12,
        clip_count=1,
        standard_wh=(720, 1280),
        pro_wh=(1080, 1920),
        export_format="mp4",
        fps_target=24,
        prompt_hint=(
            "vertical reel (9:16 full bleed, 10-12 seconds); single continuous uninterrupted shot; "
            "subject in upper 65% of frame — bottom 35% is platform UI safe zone (captions, likes, share); "
            "hook: first 2 seconds show motion toward camera, subject reveal, or high-contrast flash; "
            "rhythmically paced motion throughout; no letterboxing or black bars"
        ),
        composition_defaults={
            "duration_sec": "10-12",
            "pacing": "fast",
            "motion_intensity": "medium",
            "camera_motion": "slow_dolly_in",
            "overlay": "lower_third",
            "subtitle_safe": "on",
            "frame_safe_zone": "subject_upper_65pct",
        },
    ),
    "short_video": VideoRecipe(
        n_seconds=12,
        clip_count=5,  # 1 min total by stitching 5 clips
        standard_wh=(1280, 720),
        pro_wh=(1920, 1080),
        export_format="mp4",
        fps_target=24,
        prompt_hint=(
            "short video (1 minute) assembled from 5 clips of 12s each; narrative arc: "
            "establishing shot → development → resolution; same characters, lighting, and color grading "
            "across all clips; each clip advances the scene"
        ),
        composition_defaults={
            "duration_sec": "60",
            "clip_count": 5,
            "pacing": "medium",
            "motion_intensity": "medium",
            "camera_motion": "static_tripod_or_tracking_follow",
            "overlay": "lower_third",
            "subtitle_safe": "on",
        },
    ),
}


# =============================================================================
# Builder
# =============================================================================


class VideoArtifactsBuilder:
    """
    Implements:
      - build(): generate video from user inputs + strict per-format recipe.
      - edit(): iterate video by reusing source prompt/style and applying edit_instruction + style overrides.
    Prompt policy:
      - Primary brief first (user + strict defaults).
      - Constraints early.
      - Master content optional, appended last when include_master_content=True.

    Storage policy:
      - Individual clips uploaded to Azure blob.
      - Final asset (gif/reel/stitched) uploaded when possible.
      - Local/blob persistence delegated to orchestration artifacts persistence module.
    """

    kind = "video"
    formats = set(VIDEO_FORMATS)

    # -------------------------------------------------------------------------
    # Style helpers / merge
    # -------------------------------------------------------------------------
    @staticmethod
    def _safe_text(value: Any, fallback: str = "not specified", max_len: int = 1200) -> str:
        text = str(value or "").strip()
        return (text[:max_len] if text else fallback).strip()

    @staticmethod
    def _as_bool(value: Any, default: bool = True) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        s = str(value).strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
        return default

    @staticmethod
    def _clean_dict(d: Any) -> dict[str, Any]:
        if not isinstance(d, dict):
            return {}
        out: dict[str, Any] = {}
        for k, v in d.items():
            if v in (None, "", [], {}):
                continue
            if isinstance(v, str):
                v = v.strip()
                if not v:
                    continue
            out[k] = v
        return out

    @staticmethod
    def _merge_dicts(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
        out = dict(base or {})
        for k, v in (override or {}).items():
            if v is None:
                continue
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                merged = dict(out[k])
                merged.update({kk: vv for kk, vv in v.items() if vv is not None})
                out[k] = merged
            else:
                out[k] = v
        return out

    @staticmethod
    def _video_style_settings(ctx: PipelineContext) -> dict[str, Any]:
        """
        build(): ctx.style_settings contains full video style
        edit(): ctx.style_settings contains overrides (optional)
        """
        if isinstance(ctx.style_settings, dict) and ctx.style_settings:
            return dict(ctx.style_settings)
        if isinstance(getattr(ctx, "video_style_settings", None), dict):
            return dict(getattr(ctx, "video_style_settings", None))
        return {}

    @staticmethod
    def _resolve_recipe(fmt: str) -> VideoRecipe:
        if fmt not in VIDEO_RECIPES:
            raise ValueError(f"No video recipe configured for '{fmt}'")
        return VIDEO_RECIPES[fmt]

    @staticmethod
    def _merge_avoid(video_style: dict[str, Any]) -> list[str]:
        def canon(tag: str) -> str:
            t = re.sub(r"\s+", " ", str(tag or "").strip().lower())
            t = t.replace("-", " ")
            mapping = {
                "watermarks": "watermark",
                "watermark": "watermark",
                "logos": "logo",
                "logo": "logo",
                "ui screenshots": "ui screenshot",
                "ui screenshot": "ui screenshot",
                "readable text": "text",
                "typography": "text",
                "gibberish text": "text",
                "illegible text": "text",
            }
            if t.endswith("s") and t[:-1] in {"watermark", "logo"}:
                t = t[:-1]
            return mapping.get(t, t)

        default_avoid = ["watermarks", "logos", "ui screenshots", "real people", "readable text"]
        user_avoid = video_style.get("avoid") if isinstance(video_style.get("avoid"), list) else []
        raw = default_avoid + [str(x).strip() for x in user_avoid if str(x).strip()]

        seen: set[str] = set()
        out: list[str] = []
        for a in raw:
            key = canon(a)
            if not key or key in seen:
                continue
            seen.add(key)
            if key == "watermark":
                out.append("watermarks")
            elif key == "logo":
                out.append("logos")
            elif key == "ui screenshot":
                out.append("ui screenshots")
            elif key == "text":
                out.append("readable text")
            else:
                out.append(a)
        return out

    @staticmethod
    def _resolve_resolution(recipe: VideoRecipe, video_style: dict[str, Any]) -> tuple[int, int]:
        fidelity = str(video_style.get("output_fidelity") or "standard").strip().lower()
        if fidelity in {"pro", "hd", "high", "high_def", "high_definition"}:
            return recipe.pro_wh
        return recipe.standard_wh

    @staticmethod
    def _deployment_name() -> str:
        return str(settings.azure_video_deployment_name or "").strip()

    @staticmethod
    def _polling_controls() -> tuple[int, int]:
        def as_int(name: str, default: int, lo: int, hi: int) -> int:
            raw = str(os.getenv(name) or "").strip()
            if not raw:
                return default
            try:
                n = int(raw)
            except Exception:
                return default
            return max(lo, min(hi, n))

        max_wait = as_int("AZURE_SORA_MAX_WAIT_SECONDS", 900, 60, 3600)
        poll_interval = as_int("AZURE_SORA_POLL_INTERVAL_SECONDS", 5, 2, 60)
        return max_wait, poll_interval

    @staticmethod
    def _grounding_excerpt_for_prompt(fmt: str, ctx: PipelineContext) -> str:
        master_body = str(getattr(ctx, "master_body", "") or "").strip()
        if not master_body:
            return ""
        max_len = 240 if fmt in {"gif", "reel"} else 700
        return re.sub(r"\s+", " ", master_body[:max_len]).strip()

    @staticmethod
    def _normalized_video_style_snapshot(video_style: dict[str, Any], *, include_master: bool) -> dict[str, Any]:
        snap: dict[str, Any] = {
            "theme": video_style.get("theme"),
            "subject_prompt": video_style.get("core_prompt") or video_style.get("subject_prompt") or video_style.get("subject"),
            "avoid": video_style.get("avoid"),
            "mood": video_style.get("mood"),
            "lighting": video_style.get("lighting"),
            "palette_mode": video_style.get("palette_mode") or video_style.get("color_palette") or video_style.get("color_pallete"),
            "brand_colors": video_style.get("brand_colors"),
            "output_fidelity": video_style.get("output_fidelity"),
            "camera_motion": video_style.get("camera_motion") or None,
            "energy_level": video_style.get("energy_level") or None,
            "include_master_content": include_master,
        }
        return {k: v for k, v in snap.items() if v not in (None, "", [], {})}

    # -------------------------------------------------------------------------
    # Prompt building (precedence-first + include_master_content)
    # -------------------------------------------------------------------------
    def _build_prompt(self, *, fmt: str, ctx: PipelineContext, video_style: dict[str, Any], recipe: VideoRecipe) -> str:
        include_master_content = self._as_bool(video_style.get("include_master_content"), default=False)

        def safe(v: Any, n: int) -> str:
            return str(v or "").strip()[:n].strip()

        audience = ctx.target_audience if isinstance(ctx.target_audience, dict) else {}
        audience_segment = safe(audience.get("primary_segment") or "general", 120)
        tone = safe(getattr(ctx, "tone_preference", None) or "professional", 60)
        topic_title = safe(getattr(ctx, "topic_title", None) or "this topic", 140)

        theme = safe(video_style.get("theme"), 240)
        subject_prompt = safe(
            video_style.get("core_prompt") or video_style.get("subject_prompt") or video_style.get("subject"),
            1600,
        )
        mood_raw = safe(video_style.get("mood"), 80)
        mood = _expand_video_enum("mood", mood_raw) if mood_raw else ""

        lighting_raw = safe(video_style.get("lighting"), 80)
        lighting = _expand_video_enum("lighting", lighting_raw) if lighting_raw else ""

        palette_mode_raw = safe(video_style.get("palette_mode") or video_style.get("color_palette") or video_style.get("color_pallete"), 80)
        palette_mode = _expand_video_enum("palette_mode", palette_mode_raw) if palette_mode_raw else ""

        output_fidelity_raw = safe(video_style.get("output_fidelity"), 20)
        output_fidelity = _expand_video_enum("output_fidelity", output_fidelity_raw) if output_fidelity_raw else ""

        camera_motion_raw = safe(video_style.get("camera_motion"), 60)
        energy_level_raw = safe(video_style.get("energy_level"), 20)

        brand_colors = video_style.get("brand_colors") if isinstance(video_style.get("brand_colors"), dict) else {}

        avoid = self._merge_avoid(video_style)

        # Merge user overrides on top of recipe composition defaults
        effective_composition = dict(recipe.composition_defaults)
        if camera_motion_raw:
            effective_composition["camera_motion"] = camera_motion_raw
        if energy_level_raw in _VIDEO_ENERGY_LEVEL_MAP:
            pacing, intensity = _VIDEO_ENERGY_LEVEL_MAP[energy_level_raw]
            effective_composition["pacing"] = pacing
            effective_composition["motion_intensity"] = intensity

        primary: list[str] = []
        primary.append(f"FORMAT INTENT: {recipe.prompt_hint}")
        primary.append("PRIORITY: Follow the brief below strictly. Use reference context only if it does not conflict.")
        primary.append(
            f"OUTPUT: {fmt} video for '{topic_title}'. Per-clip duration: {recipe.n_seconds}s. "
            f"Clips: {recipe.clip_count}. Audience: {audience_segment}. Tone: {tone}."
        )
        if theme:
            primary.append(f"Theme: {theme}.")
        primary.append(f"SUBJECT (most important): {subject_prompt}")

        if effective_composition:
            cam_label = _expand_video_enum("camera_motion", effective_composition.get("camera_motion", "")) or effective_composition.get("camera_motion", "")
            energy_label = _expand_video_enum("energy_level", energy_level_raw) if energy_level_raw else ""
            controls_parts = []
            for k, v in effective_composition.items():
                if k == "camera_motion" and cam_label:
                    controls_parts.append(f"camera_motion={cam_label}")
                else:
                    controls_parts.append(f"{k}={v}")
            composition_line = "STANDARD COMPOSITION CONTROLS (apply strictly): " + ", ".join(controls_parts)
            if energy_label:
                composition_line += f". Overall energy: {energy_label}."
            primary.append(composition_line)

        if fmt == "gif":
            primary.append(
                "GIF rule: motion must be cyclical — start frame and end frame must be visually identical "
                "so the clip loops seamlessly. Use oscillating motion (slow zoom, bloom, parallax layer shift); "
                "avoid large linear camera moves that drift. Use bold flat tones; avoid heavy cinematic gradients "
                "or soft bokeh that degrade in a 256-color GIF palette."
            )
        if fmt == "reel":
            primary.append(
                "Reel rule: 9:16 full bleed — no letterboxing or black bars. "
                "Subject must occupy the upper 65% of the vertical frame; bottom 35% is reserved for platform UI "
                "(captions, like/share buttons). "
                "Hook: the first 2 seconds must feature motion toward camera, a subject reveal, or a high-contrast visual flash. "
                "Single uninterrupted camera move from start to end; motion should feel rhythmically paced."
            )
        if fmt == "short_video" and recipe.clip_count > 1:
            primary.append(
                "Short video rule: 5 clips form a narrative arc — establishing shot → development → resolution. "
                "Same characters, lighting setup, color grading, and location across all clips. "
                "Each clip advances the scene; avoid showing identical frames across clips. "
                "Implied cuts between clips should feel natural (match on action preferred)."
            )

        style_lines: list[str] = []
        if mood:
            style_lines.append(f"Mood: {mood}.")
        if lighting:
            style_lines.append(f"Lighting: {lighting}.")
        if palette_mode:
            style_lines.append(f"Palette mode: {palette_mode}.")
            if palette_mode_raw == "brand" and brand_colors:
                pairs = [f"{k}={v}" for k, v in brand_colors.items() if str(v).strip()]
                if pairs:
                    style_lines.append("Brand colors: " + ", ".join(pairs) + ".")
        if output_fidelity:
            style_lines.append(f"Visual quality: {output_fidelity}.")

        constraints: list[str] = []
        constraints.append("Do not generate readable on-screen text or typography (we will overlay text later).")
        if avoid:
            constraints.append("Avoid: " + ", ".join(avoid) + ".")

        reference_block = ""
        if include_master_content:
            ref_parts: list[str] = []
            core_idea = safe(getattr(ctx, "core_idea", None) or "", 240)
            if core_idea:
                ref_parts.append(f"Core idea: {core_idea}")
            excerpt = self._grounding_excerpt_for_prompt(fmt, ctx)
            if excerpt:
                ref_parts.append(f"Master context cues: {excerpt}")
            if ref_parts:
                reference_block = "REFERENCE CONTEXT (lowest priority, inspiration only): " + " | ".join(ref_parts)[:900]

        blocks = [
            "PRIMARY VIDEO BRIEF:\n" + "\n".join(primary),
            "VISUAL STYLE:\n" + ("\n".join(style_lines) if style_lines else "Use a coherent visual style consistent with the brief."),
            "CONSTRAINTS:\n" + "\n".join(constraints),
        ]
        if reference_block:
            blocks.append(reference_block)

        return "\n\n".join(blocks)

    @staticmethod
    def _build_segments(*, clip_count: int, base_prompt: str) -> list[dict[str, Any]]:
        n = max(1, int(clip_count))
        use_story_arc = n == len(_SHORT_VIDEO_SEGMENT_ROLES)
        segments: list[dict[str, Any]] = []
        for i in range(1, n + 1):
            if use_story_arc:
                role = _SHORT_VIDEO_SEGMENT_ROLES.get(i, f"Segment {i}/{n}: continue narrative progression.")
                seg_prompt = (
                    f"{base_prompt}\n\n"
                    f"SEGMENT {i}/{n} — {role}\n"
                    f"Maintain consistent lighting, color palette, and visual identity with all other segments.\n"
                )
            else:
                seg_prompt = (
                    f"{base_prompt}\n\n"
                    f"SEGMENT {i}/{n}:\n"
                    f"Maintain continuity with other segments; consistent setting and style.\n"
                )
            segments.append({"index": i, "prompt": seg_prompt})
        return segments

    # -------------------------------------------------------------------------
    # Generation + exporting
    # -------------------------------------------------------------------------
    def _generate_clips(
        self,
        *,
        cfg: AzureSoraPreviewConfig,
        deployment_name: str,
        fmt: str,
        ctx: PipelineContext,
        recipe: VideoRecipe,
        width: int,
        height: int,
        segments: list[dict[str, Any]],
        max_wait_seconds: int,
        poll_interval_seconds: int,
        target_artifact_id: str | None = None,
        filename_prefix: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[Path], list[str]]:
        project_id = str(getattr(ctx, "project_id", "") or "")
        user_id = str(getattr(ctx, "user_id", "") or "")
        topic_title = str(getattr(ctx, "topic_title", "") or "")

        assets: list[dict[str, Any]] = []
        local_mp4_paths: list[Path] = []
        errors: list[str] = []

        for seg in segments:
            seg_idx = int(seg.get("index") or 0)
            seg_prompt = str(seg.get("prompt") or "").strip()
            if not seg_prompt:
                errors.append(f"Missing prompt for segment {seg_idx}")
                continue

            job_id, err = _sora_create_job(
                cfg=cfg,
                deployment_name=deployment_name,
                prompt=seg_prompt,
                width=width,
                height=height,
                n_seconds=int(recipe.n_seconds),
                n_variants=1,
                timeout_s=60.0,
            )
            if err or not job_id:
                errors.append(err or f"Failed to create job for segment {seg_idx}")
                continue

            status_payload, poll_err = _sora_poll_job(
                cfg=cfg,
                job_id=job_id,
                max_wait_seconds=max_wait_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
            if poll_err or not status_payload:
                errors.append(poll_err or f"Polling failed for job {job_id}")
                continue

            status = str(status_payload.get("status") or "").lower()
            if status != "succeeded":
                failure_reason = str(status_payload.get("failure_reason") or "").strip()
                errors.append(f"Job {job_id} ended with status={status}. {failure_reason}".strip())
                continue

            generations = status_payload.get("generations", []) if isinstance(status_payload.get("generations"), list) else []
            if not generations:
                errors.append(f"Job {job_id} succeeded but returned no generations.")
                continue

            generation_id = str(generations[0].get("id") or "").strip()
            if not generation_id:
                errors.append(f"Job {job_id} generation missing id.")
                continue

            mp4_bytes, dl_err = _sora_download_video(cfg=cfg, generation_id=generation_id, timeout_s=180.0)
            if dl_err or not mp4_bytes:
                errors.append(dl_err or f"Failed to download video for generation {generation_id}")
                continue

            saved = save_video_bytes_to_local(
                data=mp4_bytes,
                ext="mp4",
                project_id=project_id,
                topic_title=topic_title,
                prefix=f"{fmt}_clip{seg_idx}",
            )
            if saved:
                local_mp4_paths.append(saved)

            # Deterministic naming support for versioning.
            # Orchestrator can pass target_artifact_id and filename_prefix like "<source_slug>_v2".
            file_prefix = (filename_prefix or "").strip() or f"{fmt}_clip_{seg_idx}"
            filename = saved.name if saved else f"{file_prefix}_{int(time.time()*1000)}.mp4"

            # Keep clip artifact_id stable per "target_artifact_id" if provided, else derive.
            # NOTE: If target_artifact_id is a single id for the whole artifact, we suffix it per segment.
            base_id = str(target_artifact_id or "").strip()
            artifact_key = f"{base_id}_seg{seg_idx}" if base_id else (saved.stem if saved else f"{fmt}_clip_{seg_idx}_{int(time.time()*1000)}")

            blob_ref = upload_artifact_bytes(
                data=mp4_bytes,
                user_id=user_id or "user",
                project_id=project_id or "project",
                fmt=fmt,
                artifact_id=artifact_key,
                filename=filename,
                content_type="video/mp4",
            )
            uri = blob_ref["uri"] if blob_ref else (str(saved) if saved else f"azure_sora_preview://generation/{generation_id}")

            assets.append(
                {
                    "type": "video_clip",
                    "segment_index": seg_idx,
                    "format": "mp4",
                    "mime_type": "video/mp4",
                    "uri": uri,
                    "path": str(saved) if saved else None,
                    "blob_path": (blob_ref or {}).get("blob_path"),
                    "source": "azure_blob" if blob_ref else ("local_disk" if saved else "azure_ref"),
                    "provider_job_id": job_id,
                    "provider_generation_id": generation_id,
                    "seconds": recipe.n_seconds,
                    "width": width,
                    "height": height,
                }
            )

        return assets, [p for p in local_mp4_paths if p.exists()], errors

    def _export_final_asset(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        recipe: VideoRecipe,
        local_clip_paths: list[Path],
        target_artifact_id: str | None = None,
        filename_prefix: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        project_id = str(getattr(ctx, "project_id", "") or "")
        user_id = str(getattr(ctx, "user_id", "") or "")
        topic_title = str(getattr(ctx, "topic_title", "") or "")
        video_output_dir().mkdir(parents=True, exist_ok=True)

        if not local_clip_paths:
            return None, "No local clip files available for export (stitch/convert skipped)."

        # Reel: treat first clip as final
        if fmt == "reel":
            p = local_clip_paths[0]
            if not p.exists():
                return None, "Reel clip missing on disk."
            data = p.read_bytes()
            base = re.sub(r"[^\w\-]", "_", (filename_prefix or topic_title or "reel")[:60]).strip("_") or "reel"
            final_name = f"{base}_{int(time.time()*1000)}.mp4"
            artifact_key = str(target_artifact_id or "").strip() or f"reel_final_{int(time.time()*1000)}"
            blob_ref = upload_artifact_bytes(
                data=data,
                user_id=user_id or "user",
                project_id=project_id or "project",
                fmt="reel_final",
                artifact_id=artifact_key,
                filename=final_name,
                content_type="video/mp4",
            )
            uri = blob_ref["uri"] if blob_ref else str(p)
            return {
                "type": "video_final",
                "format": "mp4",
                "mime_type": "video/mp4",
                "uri": uri,
                "path": str(p),
                "blob_path": (blob_ref or {}).get("blob_path"),
                "source": "azure_blob" if blob_ref else "local_disk",
            }, None

        # short_video: stitch
        if fmt == "short_video":
            if len(local_clip_paths) < recipe.clip_count:
                return None, f"Expected {recipe.clip_count} local clips for stitching, found {len(local_clip_paths)}."

            out_mp4 = save_video_bytes_to_local(
                data=b"",
                ext="mp4",
                project_id=project_id,
                topic_title=topic_title,
                prefix=f"{fmt}_final",
            )
            if not out_mp4:
                out_mp4 = video_output_dir() / f"{fmt}_final_{int(time.time()*1000)}.mp4"

            stitched, err = _concat_mp4(local_clip_paths[: recipe.clip_count], out_path=out_mp4)
            if err or not stitched:
                return None, f"Stitching failed: {err}"

            data = stitched.read_bytes()
            artifact_key = str(target_artifact_id or "").strip() or stitched.stem
            base = re.sub(r"[^\w\-]", "_", (filename_prefix or stitched.stem)[:80]).strip("_") or stitched.stem
            final_name = f"{base}_{int(time.time()*1000)}.mp4"
            blob_ref = upload_artifact_bytes(
                data=data,
                user_id=user_id or "user",
                project_id=project_id or "project",
                fmt="short_video_final",
                artifact_id=artifact_key,
                filename=final_name,
                content_type="video/mp4",
            )
            uri = blob_ref["uri"] if blob_ref else str(stitched)
            return {
                "type": "video_final",
                "format": "mp4",
                "mime_type": "video/mp4",
                "uri": uri,
                "path": str(stitched),
                "blob_path": (blob_ref or {}).get("blob_path"),
                "source": "azure_blob" if blob_ref else "local_disk",
            }, None

        # gif: mp4 -> gif
        if fmt == "gif":
            mp4_path = local_clip_paths[0]
            if not mp4_path.exists():
                return None, "GIF source clip missing on disk."

            out_gif = video_output_dir() / f"gif_final_{int(time.time()*1000)}.gif"
            gif_path, err = _mp4_to_gif(mp4_path=mp4_path, gif_path=out_gif, fps=recipe.fps_target, width=720)
            if err or not gif_path:
                return None, f"GIF conversion failed: {err}"

            data = gif_path.read_bytes()
            artifact_key = str(target_artifact_id or "").strip() or gif_path.stem
            base = re.sub(r"[^\w\-]", "_", (filename_prefix or gif_path.stem)[:80]).strip("_") or gif_path.stem
            final_name = f"{base}_{int(time.time()*1000)}.gif"
            blob_ref = upload_artifact_bytes(
                data=data,
                user_id=user_id or "user",
                project_id=project_id or "project",
                fmt="gif_final",
                artifact_id=artifact_key,
                filename=final_name,
                content_type="image/gif",
            )
            uri = blob_ref["uri"] if blob_ref else str(gif_path)
            return {
                "type": "gif_final",
                "format": "gif",
                "mime_type": "image/gif",
                "uri": uri,
                "path": str(gif_path),
                "blob_path": (blob_ref or {}).get("blob_path"),
                "source": "azure_blob" if blob_ref else "local_disk",
            }, None

        return None, f"No export logic for format '{fmt}'."

    # -------------------------------------------------------------------------
    # Validation: required UI inputs
    # -------------------------------------------------------------------------
    @staticmethod
    def _validate_required_video_inputs(video_style: dict[str, Any]) -> list[str]:
        theme = str(video_style.get("theme") or "").strip()
        subject = str(video_style.get("core_prompt") or video_style.get("subject_prompt") or video_style.get("subject") or "").strip()
        missing: list[str] = []
        if not theme:
            missing.append("theme")
        if not subject:
            missing.append("subject/core_prompt")
        return missing

    # -------------------------------------------------------------------------
    # build()
    # -------------------------------------------------------------------------
    def build(self, *, fmt: str, ctx: PipelineContext) -> ArtifactDraft:
        if fmt not in self.formats:
            raise ValueError(f"Unsupported video format for video builder: {fmt}")

        recipe = self._resolve_recipe(fmt)
        cfg = _get_azure_sora_preview_config()
        deployment_name = self._deployment_name()
        video_style = self._video_style_settings(ctx)

        payload = default_payload_template()

        # Validate config
        if not cfg:
            payload["settings"] = {
                "format": fmt,
                "generation_source": "azure_sora_preview",
                "video_generation_status": "failed",
                "error_message": "Missing Azure video config in settings (azure_video_endpoint / azure_video_api_version / azure_api_key).",
            }
            title = str(getattr(ctx, "topic_title", "") or "").strip() or f"video - {fmt}"
            tags = [str(x).strip() for x in (ctx.seed_keywords or []) if str(x).strip()]
            return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status="failed")

        if not deployment_name:
            payload["settings"] = {
                "format": fmt,
                "generation_source": "azure_sora_preview",
                "video_generation_status": "failed",
                "error_message": "Missing Azure video deployment name in settings (azure_video_deployment_name).",
            }
            title = str(getattr(ctx, "topic_title", "") or "").strip() or f"video - {fmt}"
            tags = [str(x).strip() for x in (ctx.seed_keywords or []) if str(x).strip()]
            return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status="failed")

        # Validate mandatory user inputs
        missing_inputs = self._validate_required_video_inputs(video_style)
        if missing_inputs:
            payload["settings"] = {
                "format": fmt,
                "generation_source": "azure_sora_preview",
                "video_generation_status": "failed",
                "error_message": f"Missing required video style input(s): {', '.join(missing_inputs)}.",
            }
            title = str(getattr(ctx, "topic_title", "") or "").strip() or f"video - {fmt}"
            tags = [str(x).strip() for x in (ctx.seed_keywords or []) if str(x).strip()]
            return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status="failed")

        width, height = self._resolve_resolution(recipe, video_style)
        max_wait_seconds, poll_interval_seconds = self._polling_controls()

        base_prompt = self._build_prompt(fmt=fmt, ctx=ctx, video_style=video_style, recipe=recipe)
        segments = self._build_segments(clip_count=recipe.clip_count, base_prompt=base_prompt)

        clip_assets, local_clip_paths, errors = self._generate_clips(
            cfg=cfg,
            deployment_name=deployment_name,
            fmt=fmt,
            ctx=ctx,
            recipe=recipe,
            width=width,
            height=height,
            segments=segments,
            max_wait_seconds=max_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

        final_asset: dict[str, Any] | None = None
        if clip_assets:
            final_asset, final_err = self._export_final_asset(
                fmt=fmt,
                ctx=ctx,
                recipe=recipe,
                local_clip_paths=local_clip_paths,
            )
            if final_err:
                logger.error("Video final export failed: fmt=%s project_id=%s error=%s", fmt, getattr(ctx, "project_id", ""), final_err)
                errors.append(final_err)

        payload["body"] = None
        payload["assets"] = list(clip_assets)
        if final_asset:
            payload["assets"].append(final_asset)

        payload["prompts"] = [{"name": "video_prompt", "text": base_prompt, "tool": "azure_sora_preview"}]

        stitch_plan = {
            "clip_count": recipe.clip_count,
            "clip_seconds": recipe.n_seconds,
            "segments": [{"index": s["index"]} for s in segments],
            "output": recipe.export_format,
            "convert_to_gif": True if fmt == "gif" else False,
            "loop_gif": True if fmt == "gif" else False,
            "fps_target": recipe.fps_target,
            "ffmpeg_available": _ffmpeg_exists(),
        }

        status = "generated" if clip_assets else "failed"
        if clip_assets and fmt in {"short_video", "gif"} and not final_asset:
            status = "partial"

        include_master = self._as_bool(video_style.get("include_master_content"), default=False)

        payload["settings"] = {
            "format": fmt,
            "generation_source": "azure_sora_preview",
            "video_generation_status": status,
            "deployment_name": deployment_name,
            "width": width,
            "height": height,
            "seconds": recipe.n_seconds,
            "clip_count": recipe.clip_count,
            "composition_defaults": recipe.composition_defaults,
            "stitch_plan": stitch_plan,
            "video_style": self._normalized_video_style_snapshot(video_style, include_master=include_master),
        }

        if errors:
            payload["settings"]["error_message"] = "; ".join([e for e in errors if e])[:2000]

        payload["notes"] = (
            "Generated video via Azure Sora 1 (preview). Prompt is precedence-first (user + format defaults first). "
            "Master content is optional and appended only when include_master_content=true. "
            "Clips are uploaded individually. short_video is stitched when ffmpeg is available; gif is converted when ffmpeg is available."
        )

        # Title/tags
        custom_title = ""
        if isinstance(getattr(ctx, "style_settings", None), dict):
            custom_title = str(ctx.style_settings.get("default_artifact_title") or "").strip()
        if custom_title and len(getattr(ctx, "requested_formats", []) or []) > 1:
            title = f"{custom_title} - {fmt.replace('_', ' ').title()}"
        else:
            title = custom_title or f"{getattr(ctx, 'topic_title', '')} - {fmt}".strip(" -")
        tags = [str(x).strip() for x in (ctx.seed_keywords or []) if str(x).strip()]

        return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status=status)

    # -------------------------------------------------------------------------
    # edit(): iterate video
    # -------------------------------------------------------------------------
    def edit(
        self,
        *,
        fmt: str,
        ctx: PipelineContext,
        source_artifact: dict[str, Any],
        edit_instruction: str,
        target_artifact_id: str | None = None,
        source_blob_paths: list[str] | None = None,
        filename_prefix: str | None = None,
    ) -> ArtifactDraft:
        _ = source_blob_paths  # kept for future image-to-video / video-to-video workflows

        if fmt not in self.formats:
            raise ValueError(f"Unsupported video format for video builder edit: {fmt}")

        cleaned_instruction = str(edit_instruction or "").strip()
        if not cleaned_instruction:
            raise ValueError("edit_instruction is required")

        recipe = self._resolve_recipe(fmt)
        cfg = _get_azure_sora_preview_config()
        deployment_name = self._deployment_name()
        payload = default_payload_template()

        # Extract source payload/style/prompt
        source_id = str(source_artifact.get("artifact_id") or source_artifact.get("id") or "").strip()
        source_payload = source_artifact.get("payload_json") if isinstance(source_artifact, dict) else {}
        source_payload = source_payload if isinstance(source_payload, dict) else {}
        source_settings = source_payload.get("settings") if isinstance(source_payload.get("settings"), dict) else {}
        source_prompts = source_payload.get("prompts") if isinstance(source_payload.get("prompts"), list) else []

        # Prefer original video prompt if present
        original_prompt = ""
        for item in source_prompts:
            if isinstance(item, dict) and str(item.get("name") or "") in {"video_prompt", "prompt"}:
                t = str(item.get("text") or "").strip()
                if t:
                    original_prompt = t
                    break
        if not original_prompt:
            for item in source_prompts:
                if not isinstance(item, dict):
                    continue
                t = str(item.get("text") or "").strip()
                if t:
                    original_prompt = t
                    break

        base_style = source_settings.get("video_style") if isinstance(source_settings.get("video_style"), dict) else {}
        override_style = self._video_style_settings(ctx)  # overrides from UI
        effective_style = self._merge_dicts(self._clean_dict(base_style), self._clean_dict(override_style))

        # Ensure include_master_content flag can be overridden (default False for video)
        if "include_master_content" not in effective_style and "include_master_content" in base_style:
            effective_style["include_master_content"] = base_style.get("include_master_content")

        if not original_prompt:
            original_prompt = self._build_prompt(fmt=fmt, ctx=ctx, video_style=effective_style, recipe=recipe)

        revised_prompt = (
            f"{original_prompt}\n\n"
            "ITERATION REQUEST (apply these changes while preserving core scene identity):\n"
            f"{cleaned_instruction}\n"
        ).strip()

        # Validate config
        if not cfg or not deployment_name:
            payload["body"] = None
            payload["assets"] = []
            payload["prompts"] = [
                {"name": "original_prompt", "text": original_prompt, "tool": "source_artifact"},
                {"name": "iterate_instruction", "text": cleaned_instruction, "tool": "user"},
                {"name": "video_prompt", "text": revised_prompt, "tool": "azure_sora_preview"},
            ]
            payload["settings"] = {
                "format": fmt,
                "generation_source": "iterate_edit",
                "video_generation_status": "failed",
                "error_message": "Missing Azure Sora config/deployment for iterate edit.",
                "edit_instruction": cleaned_instruction,
            }
            title = str(source_artifact.get("title") or "").strip() or f"{getattr(ctx, 'topic_title', '')} - {fmt}".strip(" -")
            tags = source_artifact.get("tags_json") if isinstance(source_artifact, dict) and isinstance(source_artifact.get("tags_json"), list) else []
            if not tags:
                tags = [str(x).strip() for x in (ctx.seed_keywords or []) if str(x).strip()]
            return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status="failed")

        # Validate required inputs AFTER merge (so overrides can satisfy them)
        missing_inputs = self._validate_required_video_inputs(effective_style)
        if missing_inputs:
            payload["settings"] = {
                "format": fmt,
                "generation_source": "iterate_edit",
                "video_generation_status": "failed",
                "error_message": f"Missing required video style input(s): {', '.join(missing_inputs)}.",
                "edit_instruction": cleaned_instruction,
            }
            title = str(source_artifact.get("title") or "").strip() or f"{getattr(ctx, 'topic_title', '')} - {fmt}".strip(" -")
            tags = source_artifact.get("tags_json") if isinstance(source_artifact, dict) and isinstance(source_artifact.get("tags_json"), list) else []
            if not tags:
                tags = [str(x).strip() for x in (ctx.seed_keywords or []) if str(x).strip()]
            return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status="failed")

        width, height = self._resolve_resolution(recipe, effective_style)
        max_wait_seconds, poll_interval_seconds = self._polling_controls()
        segments = self._build_segments(clip_count=recipe.clip_count, base_prompt=revised_prompt)

        clip_assets, local_clip_paths, errors = self._generate_clips(
            cfg=cfg,
            deployment_name=deployment_name,
            fmt=fmt,
            ctx=ctx,
            recipe=recipe,
            width=width,
            height=height,
            segments=segments,
            max_wait_seconds=max_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
            target_artifact_id=target_artifact_id,
            filename_prefix=filename_prefix,
        )

        final_asset: dict[str, Any] | None = None
        if clip_assets:
            final_asset, final_err = self._export_final_asset(
                fmt=fmt,
                ctx=ctx,
                recipe=recipe,
                local_clip_paths=local_clip_paths,
                target_artifact_id=target_artifact_id,
                filename_prefix=filename_prefix,
            )
            if final_err:
                logger.error("Video final export failed during iterate: fmt=%s project_id=%s error=%s", fmt, getattr(ctx, "project_id", ""), final_err)
                errors.append(final_err)

        payload["body"] = None
        payload["assets"] = list(clip_assets)
        if final_asset:
            payload["assets"].append(final_asset)

        payload["prompts"] = [
            {"name": "original_prompt", "text": original_prompt, "tool": "source_artifact"},
            {"name": "iterate_instruction", "text": cleaned_instruction, "tool": "user"},
            {"name": "video_prompt", "text": revised_prompt, "tool": "azure_sora_preview"},
        ]

        stitch_plan = {
            "clip_count": recipe.clip_count,
            "clip_seconds": recipe.n_seconds,
            "segments": [{"index": s["index"]} for s in segments],
            "output": recipe.export_format,
            "convert_to_gif": True if fmt == "gif" else False,
            "loop_gif": True if fmt == "gif" else False,
            "fps_target": recipe.fps_target,
            "ffmpeg_available": _ffmpeg_exists(),
        }

        status = "generated" if clip_assets else "failed"
        if clip_assets and fmt in {"short_video", "gif"} and not final_asset:
            status = "partial"

        include_master = self._as_bool(effective_style.get("include_master_content"), default=False)

        payload["settings"] = {
            "format": fmt,
            "generation_source": "iterate_edit",
            "video_generation_status": status,
            "deployment_name": deployment_name,
            "width": width,
            "height": height,
            "seconds": recipe.n_seconds,
            "clip_count": recipe.clip_count,
            "composition_defaults": recipe.composition_defaults,
            "stitch_plan": stitch_plan,
            "edit_instruction": cleaned_instruction,
            "video_style": self._normalized_video_style_snapshot(effective_style, include_master=include_master),
            "source_artifact_id": source_id or None,
        }

        if errors:
            payload["settings"]["error_message"] = "; ".join([e for e in errors if e])[:2000]

        payload["notes"] = "Video iteration generated from original prompt + iterate instruction (prompt-regeneration)."

        title = str(source_artifact.get("title") or "").strip() if isinstance(source_artifact, dict) else ""
        if not title:
            title = f"{getattr(ctx, 'topic_title', '')} - {fmt}".strip(" -")

        tags = (
            source_artifact.get("tags_json")
            if isinstance(source_artifact, dict) and isinstance(source_artifact.get("tags_json"), list)
            else []
        )
        if not tags:
            tags = [str(x).strip() for x in (ctx.seed_keywords or []) if str(x).strip()]

        return ArtifactDraft(format=fmt, title=title, payload_json=payload, tags_json=tags, status=status)


BUILDER = VideoArtifactsBuilder()
