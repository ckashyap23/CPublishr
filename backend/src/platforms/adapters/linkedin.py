from __future__ import annotations

import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInAdapter:
    platform_name = "linkedin"
    api_base = "https://api.linkedin.com/rest"

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
    def _source_artifact(source: dict[str, Any]) -> dict[str, Any]:
        a = source.get("artifact") if isinstance(source, dict) else None
        return a if isinstance(a, dict) else {}

    @staticmethod
    def _normalize_hashtag(tag: str) -> str:
        t = str(tag or "").strip()
        if not t:
            return ""
        if t.startswith("#"):
            return t
        return f"#{''.join(t.split())}"

    @classmethod
    def _render_text_source(cls, source: dict[str, Any]) -> str:
        value = cls._artifact_part_value(source)
        part = str(source.get("part") or "").strip().lower()
        if part == "tags_json":
            tags = [cls._normalize_hashtag(x) for x in (value or [])]
            tags = [t for t in tags if t]
            return " ".join(tags)
        if part == "items" and isinstance(value, list):
            texts = [str(v.get("text") or "").strip() for v in value if isinstance(v, dict)]
            texts = [t for t in texts if t]
            return "\n".join(texts)
        if isinstance(value, list):
            return "\n".join(str(x).strip() for x in value if str(x).strip())
        return str(value or "").strip()

    @classmethod
    def _merge_text_sources(cls, sources: list[dict[str, Any]]) -> str:
        chunks = [cls._render_text_source(s) for s in (sources or [])]
        chunks = [c for c in chunks if c]
        return "\n\n".join(chunks).strip()

    @classmethod
    def _extract_media_assets(cls, sources: list[dict[str, Any]], *, allowed_prefix: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for source in sources or []:
            value = cls._artifact_part_value(source)
            artifact = cls._source_artifact(source)
            artifact_title = str(artifact.get("title") or "").strip()
            if isinstance(value, list):
                for asset in value:
                    if not isinstance(asset, dict):
                        continue
                    mime = str(asset.get("mime_type") or "").strip().lower()
                    if allowed_prefix and not mime.startswith(allowed_prefix):
                        continue
                    out.append({"asset": asset, "artifact_title": artifact_title, "artifact": artifact, "source": source})
        return out

    @staticmethod
    def _read_asset_bytes(asset: dict[str, Any]) -> tuple[bytes, str, str]:
        """Return bytes, content_type, display_name."""
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

        if uri.startswith("http://") or uri.startswith("https://"):
            req = Request(uri, method="GET")
            with urlopen(req, timeout=max(5, int(settings.linkedin_http_timeout_seconds or 60))) as resp:  # nosec B310
                data = resp.read()
                content_type = str(resp.headers.get("Content-Type") or mime_type or "application/octet-stream")
                path_part = urlparse(uri).path or ""
                display_name = Path(path_part).name or "remote_asset.bin"
                return data, content_type, display_name

        raise ValueError(f"Unable to read asset bytes from path/uri (path={path!r}, uri={uri!r})")

    @staticmethod
    def _json_headers() -> dict[str, str]:
        token = (settings.linkedin_access_token or "").strip()
        version = (settings.linkedin_api_version or "").strip() or "202602"
        if not token:
            raise ValueError("LinkedIn publishing is not configured: linkedin_access_token is missing")
        return {
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": version,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _binary_headers(content_type: str) -> dict[str, str]:
        token = (settings.linkedin_access_token or "").strip()
        version = (settings.linkedin_api_version or "").strip() or "202602"
        if not token:
            raise ValueError("LinkedIn publishing is not configured: linkedin_access_token is missing")
        return {
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": version,
            "Content-Type": content_type or "application/octet-stream",
        }

    @staticmethod
    def _http_json(method: str, url: str, *, headers: dict[str, str], body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any], dict[str, str]]:
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = Request(url, data=data, method=method.upper())
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urlopen(req, timeout=max(5, int(settings.linkedin_http_timeout_seconds or 60))) as resp:  # nosec B310
                raw = resp.read()
                text = raw.decode("utf-8", errors="replace") if raw else ""
                payload = json.loads(text) if text else {}
                return int(resp.status), (payload if isinstance(payload, dict) else {}), dict(resp.headers.items())
        except HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            text = raw.decode("utf-8", errors="replace") if raw else str(exc)
            raise ValueError(f"LinkedIn API error {exc.code} for {method} {url}: {text}") from exc
        except URLError as exc:
            raise ValueError(f"LinkedIn API connection error for {method} {url}: {exc}") from exc

    @staticmethod
    def _http_put_binary(url: str, *, headers: dict[str, str], data: bytes) -> dict[str, str]:
        req = Request(url, data=data, method="PUT")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urlopen(req, timeout=max(10, int(settings.linkedin_http_timeout_seconds or 60))) as resp:  # nosec B310
                # PUT upload typically returns empty body; ETag is important for video finalize.
                return dict(resp.headers.items())
        except HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            text = raw.decode("utf-8", errors="replace") if raw else str(exc)
            raise ValueError(f"LinkedIn upload error {exc.code} for PUT {url}: {text}") from exc
        except URLError as exc:
            raise ValueError(f"LinkedIn upload connection error for PUT {url}: {exc}") from exc

    @classmethod
    def _initialize_upload(cls, media_kind: str, owner_urn: str, *, file_size_bytes: int | None = None) -> dict[str, Any]:
        endpoint = f"{cls.api_base}/{media_kind}s?action=initializeUpload"
        req: dict[str, Any] = {"owner": owner_urn}
        if media_kind == "video":
            req["fileSizeBytes"] = int(file_size_bytes or 0)
            req["uploadCaptions"] = False
            req["uploadThumbnail"] = False
        status, payload, _ = cls._http_json(
            "POST",
            endpoint,
            headers=cls._json_headers(),
            body={"initializeUploadRequest": req},
        )
        if status not in (200, 201):
            raise ValueError(f"LinkedIn initialize {media_kind} upload failed with status {status}")
        value = payload.get("value") if isinstance(payload, dict) else None
        if not isinstance(value, dict):
            raise ValueError(f"LinkedIn initialize {media_kind} upload response missing value")
        return value

    @classmethod
    def _upload_image(cls, owner_urn: str, *, data: bytes, content_type: str) -> str:
        init = cls._initialize_upload("image", owner_urn)
        upload_url = str(init.get("uploadUrl") or "").strip()
        image_urn = str(init.get("image") or "").strip()
        if not upload_url or not image_urn:
            raise ValueError("LinkedIn image initialize response missing uploadUrl/image URN")
        cls._http_put_binary(upload_url, headers=cls._binary_headers(content_type), data=data)
        return image_urn

    @classmethod
    def _upload_document(cls, owner_urn: str, *, data: bytes, content_type: str) -> str:
        init = cls._initialize_upload("document", owner_urn)
        upload_url = str(init.get("uploadUrl") or "").strip()
        document_urn = str(init.get("document") or "").strip()
        if not upload_url or not document_urn:
            raise ValueError("LinkedIn document initialize response missing uploadUrl/document URN")
        cls._http_put_binary(upload_url, headers=cls._binary_headers(content_type), data=data)
        return document_urn

    @classmethod
    def _upload_video(cls, owner_urn: str, *, data: bytes, content_type: str) -> str:
        init = cls._initialize_upload("video", owner_urn, file_size_bytes=len(data))
        video_urn = str(init.get("video") or "").strip()
        upload_token = str(init.get("uploadToken") or "")
        instructions = init.get("uploadInstructions")
        if not video_urn or not isinstance(instructions, list) or not instructions:
            raise ValueError("LinkedIn video initialize response missing video URN/uploadInstructions")

        uploaded_part_ids: list[str] = []
        for ins in instructions:
            if not isinstance(ins, dict):
                continue
            upload_url = str(ins.get("uploadUrl") or "").strip()
            first = int(ins.get("firstByte") or 0)
            last = int(ins.get("lastByte") or -1)
            if not upload_url or first < 0 or last < first:
                raise ValueError("LinkedIn video upload instruction invalid")
            chunk = data[first : last + 1]
            headers = cls._http_put_binary(upload_url, headers=cls._binary_headers(content_type), data=chunk)
            etag = str(headers.get("ETag") or headers.get("Etag") or "").strip()
            if etag:
                uploaded_part_ids.append(etag)

        finalize_body = {
            "finalizeUploadRequest": {
                "video": video_urn,
                "uploadToken": upload_token,
                "uploadedPartIds": uploaded_part_ids,
            }
        }
        status, _, _ = cls._http_json(
            "POST",
            f"{cls.api_base}/videos?action=finalizeUpload",
            headers=cls._json_headers(),
            body=finalize_body,
        )
        if status not in (200, 201):
            raise ValueError(f"LinkedIn video finalize failed with status {status}")
        return video_urn

    @classmethod
    def _create_post(
        cls,
        *,
        author_urn: str,
        commentary: str,
        media_content: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "author": author_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if media_content:
            body["content"] = media_content
        status, payload, headers = cls._http_json(
            "POST",
            f"{cls.api_base}/posts",
            headers=cls._json_headers(),
            body=body,
        )
        if status not in (200, 201):
            raise ValueError(f"LinkedIn create post failed with status {status}")
        post_id = str(headers.get("x-restli-id") or headers.get("X-RestLi-Id") or "").strip() or None
        return {
            "status": "published",
            "post_id": post_id,
            "response_body": payload or {},
            "response_headers": headers,
        }

    @staticmethod
    def _slug(value: str, fallback: str) -> str:
        s = re.sub(r"[^\w\-]+", "_", str(value or "").strip()).strip("_")
        return s or fallback

    @staticmethod
    def _join_prefix(*parts: str) -> str:
        return "/".join([str(p).strip().strip("/") for p in parts if str(p).strip()])

    @staticmethod
    def _to_hashtags(tags: list[str]) -> str:
        out = []
        seen = set()
        for t in tags or []:
            n = LinkedInAdapter._normalize_hashtag(str(t))
            if not n:
                continue
            k = n.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(n)
        return " ".join(out).strip()

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

    @staticmethod
    def _pick_media_mode(image_assets: list[dict[str, Any]], video_assets: list[dict[str, Any]], document_assets: list[dict[str, Any]]) -> str:
        selected = [
            ("image", bool(image_assets)),
            ("video", bool(video_assets)),
            ("document", bool(document_assets)),
        ]
        active = [name for name, on in selected if on]
        if not active:
            return "text"
        if len(active) > 1:
            raise ValueError(f"LinkedIn publish supports one media type per post. Multiple selected: {', '.join(active)}")
        return active[0]

    def get_field_schema(self) -> dict[str, Any]:
        return {
            "platform": self.platform_name,
            "fields": [
                {
                    "field_key": "body",
                    "label": "LinkedIn Body",
                    "required": True,
                    "allows_multiple": False,
                    "accepted_artifact_formats": ["post", "caption", "cta_variants", "newsletter", "blog", "script_short"],
                    "description": "Main LinkedIn post body. Multiple mapped artifacts/sources are merged into one text block by adapter.",
                    "suggested_parts": ["body", "items", "tags_json", "title"],
                },
                {
                    "field_key": "image",
                    "label": "LinkedIn Image",
                    "required": False,
                    "allows_multiple": True,
                    "accepted_artifact_formats": ["post_image", "thumbnail", "banner", "cover"],
                    "description": "Optional LinkedIn image asset(s). Single image and multi-image are supported by adapter upload flow.",
                    "suggested_parts": ["assets"],
                },
                {
                    "field_key": "video",
                    "label": "LinkedIn Video",
                    "required": False,
                    "allows_multiple": False,
                    "accepted_artifact_formats": ["reel", "short_video", "video", "gif"],
                    "description": "Optional LinkedIn video asset.",
                    "suggested_parts": ["assets"],
                },
                {
                    "field_key": "document",
                    "label": "LinkedIn Document",
                    "required": False,
                    "allows_multiple": False,
                    "accepted_artifact_formats": ["document", "pdf_document"],
                    "description": "Optional LinkedIn document asset.",
                    "suggested_parts": ["assets"],
                },
            ],
        }

    def build_platform_payload(self, *, field_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        body_sources = field_mapping.get("body") or []
        image_sources = field_mapping.get("image") or []
        video_sources = field_mapping.get("video") or []
        document_sources = field_mapping.get("document") or []

        body_text = self._merge_text_sources(body_sources)
        image_assets = self._extract_media_assets(image_sources, allowed_prefix="image/")
        video_assets = self._extract_media_assets(video_sources, allowed_prefix="video/")
        document_assets = self._extract_media_assets(document_sources, allowed_prefix="")
        document_assets = [
            a for a in document_assets
            if str(a["asset"].get("mime_type") or "").lower().startswith(("application/", "text/"))
        ]

        return {
            "platform": self.platform_name,
            "linkedin_body": body_text,
            "linkedin_body_sources": body_sources,
            "linkedin_image_sources": image_sources,
            "linkedin_video_sources": video_sources,
            "linkedin_document_sources": document_sources,
            "media_assets": {
                "images": image_assets,
                "videos": video_assets,
                "documents": document_assets,
            },
        }

    def save_to_publish_bundle(
        self,
        *,
        payload: dict[str, Any],
        output_root: str,
        relative_path: str,
    ) -> dict[str, Any]:
        commentary = str(payload.get("linkedin_body") or "").strip()
        if not commentary:
            raise ValueError("LinkedIn body/commentary is required")

        media_assets = payload.get("media_assets") if isinstance(payload.get("media_assets"), dict) else {}
        image_assets = list(media_assets.get("images") or []) if isinstance(media_assets, dict) else []
        video_assets = list(media_assets.get("videos") or []) if isinstance(media_assets, dict) else []
        document_assets = list(media_assets.get("documents") or []) if isinstance(media_assets, dict) else []

        saved_files: list[dict[str, Any]] = []

        text_filename = "linkedin_body.txt"
        text_uri = self._save_output_bytes(
            output_root=output_root,
            relative_path=relative_path,
            filename=text_filename,
            data=commentary.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )
        saved_files.append({"type": "text", "filename": text_filename, "uri": text_uri})

        counters = {"image": 0, "video": 0, "document": 0}
        for kind, items in (("image", image_assets), ("video", video_assets), ("document", document_assets)):
            for item in items:
                asset = item.get("asset") if isinstance(item, dict) else {}
                if not isinstance(asset, dict):
                    continue
                data, content_type, display_name = self._read_asset_bytes(asset)
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
                "commentary": commentary,
                "media_counts": {
                    "images": len(image_assets),
                    "videos": len(video_assets),
                    "documents": len(document_assets),
                },
            },
        }

    def publish(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        # NOTE: LinkedIn API calls are intentionally disabled for now.
        # Keep this method as a non-publishing placeholder while "Save to Publish" is active.
        #
        # API implementation (upload media + create post) is preserved below and can be restored later.
        #
        # author_urn = (settings.linkedin_author_urn or "").strip()
        # if not author_urn:
        #     raise ValueError("LinkedIn publishing is not configured: linkedin_author_urn is missing")
        #
        # commentary = str(payload.get("linkedin_body") or "").strip()
        # if not commentary:
        #     raise ValueError("LinkedIn body/commentary is required")
        #
        # media_assets = payload.get("media_assets") if isinstance(payload.get("media_assets"), dict) else {}
        # image_assets = list(media_assets.get("images") or []) if isinstance(media_assets, dict) else []
        # video_assets = list(media_assets.get("videos") or []) if isinstance(media_assets, dict) else []
        # document_assets = list(media_assets.get("documents") or []) if isinstance(media_assets, dict) else []
        #
        # mode = self._pick_media_mode(image_assets, video_assets, document_assets)
        # uploaded_urns: dict[str, list[str]] = {"images": [], "videos": [], "documents": []}
        # media_content: dict[str, Any] | None = None
        #
        # if mode == "image":
        #     for item in image_assets:
        #         asset = item.get("asset") if isinstance(item, dict) else {}
        #         data, content_type, _ = self._read_asset_bytes(asset if isinstance(asset, dict) else {})
        #         uploaded_urns["images"].append(self._upload_image(author_urn, data=data, content_type=content_type))
        #
        #     if len(uploaded_urns["images"]) == 1:
        #         media_content = {
        #             "media": {
        #                 "altText": str((image_assets[0].get("artifact_title") or "LinkedIn image")).strip() or "LinkedIn image",
        #                 "id": uploaded_urns["images"][0],
        #             }
        #         }
        #     else:
        #         media_content = {
        #             "multiImage": {
        #                 "images": [{"id": urn} for urn in uploaded_urns["images"]]
        #             }
        #         }
        #
        # elif mode == "video":
        #     item = video_assets[0]
        #     asset = item.get("asset") if isinstance(item, dict) else {}
        #     data, content_type, _ = self._read_asset_bytes(asset if isinstance(asset, dict) else {})
        #     video_urn = self._upload_video(author_urn, data=data, content_type=content_type)
        #     uploaded_urns["videos"].append(video_urn)
        #     media_content = {
        #         "media": {
        #             "title": str((item.get("artifact_title") or "LinkedIn video")).strip() or "LinkedIn video",
        #             "id": video_urn,
        #         }
        #     }
        #
        # elif mode == "document":
        #     item = document_assets[0]
        #     asset = item.get("asset") if isinstance(item, dict) else {}
        #     data, content_type, display_name = self._read_asset_bytes(asset if isinstance(asset, dict) else {})
        #     doc_urn = self._upload_document(author_urn, data=data, content_type=content_type)
        #     uploaded_urns["documents"].append(doc_urn)
        #     media_content = {
        #         "media": {
        #             "title": display_name or str((item.get("artifact_title") or "Document")).strip() or "Document",
        #             "id": doc_urn,
        #         }
        #     }
        #
        # post_result = self._create_post(author_urn=author_urn, commentary=commentary, media_content=media_content)
        commentary = str(payload.get("linkedin_body") or "").strip()
        return {
            "status": "saved_only",
            "external_id": None,
            "external_url": None,
            "provider_response": {
                "mode": "linkedin_rest_disabled",
            },
            "payload": {
                "commentary": commentary,
            },
        }


ADAPTER = LinkedInAdapter()
