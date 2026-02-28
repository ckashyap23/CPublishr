from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.core.config import settings


class InstagramAdapter:
    platform_name = "instagram"

    @staticmethod
    def _artifact_part_value(source: dict[str, Any]) -> Any:
        artifact = source.get("artifact") if isinstance(source, dict) else {}
        if not isinstance(artifact, dict):
            return None
        part = str(source.get("part") or "").strip()
        if part == "title":
            return artifact.get("title")
        if part == "tags_json":
            return artifact.get("tags_json") or []
        payload = artifact.get("payload_json") if isinstance(artifact.get("payload_json"), dict) else {}
        if part == "body":
            return payload.get("body")
        if part == "items":
            return payload.get("items") or []
        if part == "assets":
            return payload.get("assets") or []
        return None

    @staticmethod
    def _normalize_hashtag(tag: str) -> str:
        t = str(tag or "").strip()
        if not t:
            return ""
        return t if t.startswith("#") else f"#{''.join(t.split())}"

    @classmethod
    def _tags_line(cls, values: list[Any]) -> str:
        out = []
        seen = set()
        for x in values or []:
            t = cls._normalize_hashtag(str(x or ""))
            if not t:
                continue
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(t)
        return " ".join(out).strip()

    @staticmethod
    def _render_source_preview(source: dict[str, Any]) -> str:
        value = InstagramAdapter._artifact_part_value(source)
        part = str(source.get("part") or "").strip().lower()
        if part == "tags_json":
            tags = [str(x).strip() for x in (value or []) if str(x).strip()]
            return InstagramAdapter._tags_line(tags)
        if part == "items" and isinstance(value, list):
            texts = [str(v.get("text") or "").strip() for v in value if isinstance(v, dict)]
            texts = [t for t in texts if t]
            return "\n".join(texts)
        if isinstance(value, list):
            return "\n".join(str(x) for x in value if str(x).strip())
        return str(value or "").strip()

    @staticmethod
    def _source_artifact(source: dict[str, Any]) -> dict[str, Any]:
        a = source.get("artifact") if isinstance(source, dict) else None
        return a if isinstance(a, dict) else {}

    @classmethod
    def _extract_media_assets(cls, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for source in sources or []:
            value = cls._artifact_part_value(source)
            artifact = cls._source_artifact(source)
            artifact_title = str(artifact.get("title") or "").strip()
            if not isinstance(value, list):
                continue
            for asset in value:
                if not isinstance(asset, dict):
                    continue
                mime = str(asset.get("mime_type") or "").strip().lower()
                if not mime.startswith(("image/", "video/", "application/", "text/")):
                    continue
                out.append({"asset": asset, "artifact_title": artifact_title, "artifact": artifact, "source": source})
        return out

    @staticmethod
    def _read_asset_bytes(asset: dict[str, Any]) -> tuple[bytes, str, str]:
        path = str(asset.get("path") or "").strip()
        uri = str(asset.get("uri") or "").strip()
        mime_type = str(asset.get("mime_type") or "").strip()
        display_name = ""

        if path:
            p = Path(path)
            if p.exists() and p.is_file():
                display_name = p.name
                data = p.read_bytes()
                content_type = mime_type or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                return data, content_type, display_name

        if uri.startswith("file://"):
            parsed = urlparse(uri)
            file_path = Path(parsed.path.lstrip("/")) if parsed.path else None
            if file_path and file_path.exists() and file_path.is_file():
                display_name = file_path.name
                data = file_path.read_bytes()
                content_type = mime_type or mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
                return data, content_type, display_name

        if uri.startswith(("http://", "https://")):
            req = Request(uri, method="GET")
            with urlopen(req, timeout=60) as resp:  # nosec B310
                data = resp.read()
                content_type = str(resp.headers.get("Content-Type") or mime_type or "application/octet-stream")
                path_part = urlparse(uri).path or ""
                display_name = Path(path_part).name or "remote_asset.bin"
                return data, content_type, display_name

        raise ValueError(f"Unable to read asset bytes from path/uri (path={path!r}, uri={uri!r})")

    @staticmethod
    def _join_prefix(*parts: str) -> str:
        return "/".join([str(p).strip().strip("/") for p in parts if str(p).strip()])

    @classmethod
    def _save_output_bytes(
        cls,
        *,
        output_root: str,
        relative_path: str,
        filename: str,
        data: bytes,
        content_type: str,
    ) -> str:
        root = str(output_root or "").strip()
        if root.lower().startswith(("azure://", "az://")):
            try:
                from azure.storage.blob import BlobServiceClient, ContentSettings  # type: ignore
            except Exception as exc:
                raise ValueError("azure-storage-blob is not installed for azure:// OUTPUT_PATH") from exc
            conn = str(settings.azure_storage_connection_string or "").strip()
            if not conn:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required for azure:// OUTPUT_PATH")
            parsed = urlparse(root)
            container = (parsed.netloc or "").strip()
            if not container:
                raise ValueError("azure:// OUTPUT_PATH must include container, e.g. azure://artifacts/base-prefix")
            prefix = (parsed.path or "").strip().strip("/")
            blob_path = cls._join_prefix(prefix, relative_path, filename)
            svc = BlobServiceClient.from_connection_string(conn)
            container_client = svc.get_container_client(container)
            try:
                container_client.create_container()
            except Exception:
                pass
            blob = container_client.get_blob_client(blob_path)
            blob.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
            return blob.url

        if root.lower().startswith("gs://"):
            try:
                from google.cloud import storage  # type: ignore
            except Exception as exc:
                raise ValueError("google-cloud-storage is not installed for gs:// OUTPUT_PATH") from exc
            parsed = urlparse(root)
            bucket_name = (parsed.netloc or "").strip()
            if not bucket_name:
                raise ValueError("gs:// OUTPUT_PATH must include bucket, e.g. gs://my-bucket/base-prefix")
            prefix = (parsed.path or "").strip().strip("/")
            blob_path = cls._join_prefix(prefix, relative_path, filename)
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(data, content_type=content_type)
            return f"gs://{bucket_name}/{blob_path}"

        base = root
        if base.lower().startswith("file://"):
            parsed = urlparse(base)
            base = parsed.path or ""
            if re.match(r"^/[A-Za-z]:", base):
                base = base[1:]
        target_dir = Path(base) / Path(relative_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / filename
        target_file.write_bytes(data)
        return str(target_file)

    def get_field_schema(self) -> dict[str, Any]:
        return {
            "platform": self.platform_name,
            "fields": [
                {
                    "field_key": "caption",
                    "label": "Instagram Caption",
                    "required": True,
                    "allows_multiple": True,
                    "accepted_artifact_formats": ["caption"],
                    "description": "Primary Instagram caption text (can combine caption + CTA variants/tags via source mapping).",
                    "suggested_parts": ["body", "tags_json"],
                },
                {
                    "field_key": "cta_variants",
                    "label": "CTA Variants",
                    "required": False,
                    "allows_multiple": True,
                    "accepted_artifact_formats": ["cta_variants"],
                    "description": "Optional CTA variants to append/select from.",
                    "suggested_parts": ["items"],
                },
                {
                    "field_key": "image",
                    "label": "Instagram Media",
                    "required": False,
                    "allows_multiple": False,
                    "accepted_artifact_formats": ["post_image", "thumbnail", "banner", "cover", "reel", "short_video", "gif", "video"],
                    "description": "Optional Instagram media asset (image or video).",
                    "suggested_parts": ["assets"],
                },
            ],
        }

    def build_platform_payload(self, *, field_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        caption_sources = field_mapping.get("caption") or []
        cta_sources = field_mapping.get("cta_variants") or []
        media_sources = field_mapping.get("image") or []

        caption_text = "\n\n".join(
            [chunk for chunk in (self._render_source_preview(s) for s in caption_sources) if chunk]
        ).strip()
        cta_text = "\n".join(
            [chunk for chunk in (self._render_source_preview(s) for s in cta_sources) if chunk]
        ).strip()
        combined_text = caption_text.strip()
        if cta_text:
            combined_text = (combined_text + "\n\n" + cta_text).strip() if combined_text else cta_text
        media_assets = self._extract_media_assets(media_sources)
        return {
            "platform": self.platform_name,
            "instagram_caption": caption_text,
            "instagram_caption_sources": caption_sources,
            "instagram_cta_text": cta_text or None,
            "instagram_cta_sources": cta_sources,
            "instagram_text_combined": combined_text,
            "instagram_media_sources": media_sources,
            "media_assets": media_assets,
        }

    def save_to_publish_bundle(
        self,
        *,
        payload: dict[str, Any],
        output_root: str,
        relative_path: str,
    ) -> dict[str, Any]:
        text_content = str(payload.get("instagram_text_combined") or "").strip()
        if not text_content:
            text_content = str(payload.get("instagram_caption") or "").strip()
        if not text_content:
            raise ValueError("Instagram caption/text is required")

        saved_files: list[dict[str, Any]] = []
        text_filename = "instagram_caption.txt"
        text_uri = self._save_output_bytes(
            output_root=output_root,
            relative_path=relative_path,
            filename=text_filename,
            data=text_content.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )
        saved_files.append({"type": "text", "filename": text_filename, "uri": text_uri})

        media_assets = list(payload.get("media_assets") or [])
        counters = {"image": 0, "video": 0, "document": 0, "other": 0}
        for item in media_assets:
            asset = item.get("asset") if isinstance(item, dict) else {}
            if not isinstance(asset, dict):
                continue
            data, content_type, display_name = self._read_asset_bytes(asset)
            mime = str(content_type or "").lower()
            if mime.startswith("image/"):
                kind = "image"
            elif mime.startswith("video/"):
                kind = "video"
            elif mime.startswith(("application/", "text/")):
                kind = "document"
            else:
                kind = "other"
            counters[kind] += 1
            safe_name = Path(display_name or f"{kind}_{counters[kind]}").name
            if not Path(safe_name).suffix:
                ext = mimetypes.guess_extension(content_type or "") or ""
                safe_name = f"{safe_name}{ext}"
            prefixed_name = f"{kind}_{counters[kind]}_{safe_name}"
            uri = self._save_output_bytes(
                output_root=output_root,
                relative_path=relative_path,
                filename=prefixed_name,
                data=data,
                content_type=content_type or "application/octet-stream",
            )
            saved_files.append({"type": kind, "filename": prefixed_name, "uri": uri})

        return {
            "status": "saved",
            "output_path": self._join_prefix(str(output_root).rstrip("/"), relative_path),
            "output_relative_path": relative_path,
            "saved_files": saved_files,
            "payload": {
                "text": text_content,
                "media_count": len(media_assets),
            },
        }

    def publish(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        # Placeholder publish. Replace with actual Instagram API integration.
        return {
            "status": "published",
            "external_id": "instagram_placeholder_media_id",
            "external_url": None,
            "provider_response": {"mode": "placeholder"},
            "payload": payload,
        }


ADAPTER = InstagramAdapter()
