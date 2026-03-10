from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from src.services.storage.artifact_blob_storage import upload_bytes, upload_text

logger = logging.getLogger(__name__)

_FORMATS_DIR = Path(__file__).resolve().parent / "formats"
_TEXT_DIR = _FORMATS_DIR / "text"
_IMAGES_DIR = _FORMATS_DIR / "images"
_VIDEOS_DIR = _FORMATS_DIR / "videos"


def text_output_dir() -> Path:
    return _TEXT_DIR


def image_output_dir() -> Path:
    return _IMAGES_DIR


def video_output_dir() -> Path:
    return _VIDEOS_DIR


def _slug_seed(value: str, *, default: str, max_len: int = 80) -> str:
    seed = re.sub(r"[^\w\-]", "_", (value or "").strip())[:max_len]
    seed = seed.strip("_")
    return seed or default


def _save_bytes(
    *,
    output_dir: Path,
    data: bytes,
    ext: str,
    seed: str,
    default_seed: str,
) -> Path | None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = _slug_seed(seed, default=default_seed, max_len=80)
        file_ext = str(ext or "").strip().lower() or "bin"
        filename = f"{slug}_{int(time.time() * 1000)}.{file_ext}"
        path = output_dir / filename
        path.write_bytes(data)
        return path
    except Exception as exc:
        logger.warning("Failed to save artifact bytes to disk (%s): %s", output_dir, exc)
        return None


def save_text_to_local(
    *,
    text: str,
    ext: str,
    project_id: str = "",
    topic_title: str = "",
    fmt: str = "",
) -> Path | None:
    seed = f"{topic_title or project_id or 'text'}_{fmt or 'artifact'}"
    return _save_bytes(
        output_dir=text_output_dir(),
        data=(text or "").encode("utf-8"),
        ext=ext,
        seed=seed,
        default_seed="text_artifact",
    )


def save_image_bytes_to_local(
    *,
    data: bytes,
    ext: str,
    project_id: str = "",
    topic_title: str = "",
) -> Path | None:
    seed = topic_title or project_id or "image"
    return _save_bytes(
        output_dir=image_output_dir(),
        data=data,
        ext=ext,
        seed=seed,
        default_seed="image",
    )


def save_video_bytes_to_local(
    *,
    data: bytes,
    ext: str,
    project_id: str = "",
    topic_title: str = "",
    prefix: str = "clip",
) -> Path | None:
    seed = topic_title or project_id or prefix
    return _save_bytes(
        output_dir=video_output_dir(),
        data=data,
        ext=ext,
        seed=seed,
        default_seed=prefix or "clip",
    )


def upload_artifact_bytes(
    *,
    data: bytes,
    user_id: str,
    project_id: str,
    fmt: str,
    artifact_id: str,
    filename: str,
    content_type: str,
) -> dict[str, str] | None:
    return upload_bytes(
        data=data,
        user_id=user_id,
        project_id=project_id,
        format=fmt,
        artifact_id=artifact_id,
        filename=filename,
        content_type=content_type,
    )


def upload_artifact_text(
    *,
    text: str,
    user_id: str,
    project_id: str,
    fmt: str,
    artifact_id: str,
    filename: str,
    content_type: str = "text/plain; charset=utf-8",
) -> dict[str, str] | None:
    return upload_text(
        text=text,
        user_id=user_id,
        project_id=project_id,
        format=fmt,
        artifact_id=artifact_id,
        filename=filename,
        content_type=content_type,
    )
