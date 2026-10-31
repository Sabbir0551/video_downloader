"""
Storage Backend Abstraction for AnyStream Video Platform.

Supports:
- LocalStorage: Saves media files to local disk under settings.STORAGE_DIR.
- R2Storage: Uploads media files to Cloudflare R2 (S3-compatible) with zero-egress presigned download URLs.

Security Requirements:
- Stored object keys MUST use random IDs only (e.g. {job_id}.{ext}), NEVER the video title.
- User-facing video titles are dynamically injected into the Content-Disposition header.
"""

import logging
import os
import shutil
import urllib.parse
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_media_content_type(file_ext: str) -> str:
    """Returns the standardized MIME type for given file extension."""
    ext = file_ext.lower().lstrip(".")
    mapping = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
        "wav": "audio/wav",
        "flac": "audio/flac",
    }
    return mapping.get(ext, "application/octet-stream")


def build_content_disposition(filename: str, file_ext: str) -> str:
    """
    Constructs an RFC 5987 / RFC 6266 compliant Content-Disposition header.
    Strict ASCII in filename fallback, UTF-8 in filename* parameter.
    """
    ext = file_ext.lstrip(".") or "mp4"
    base_name = filename
    if base_name.lower().endswith(f".{ext}"):
        base_name = base_name[: -(len(ext) + 1)]

    full_filename = f"{base_name}.{ext}"
    encoded_filename = urllib.parse.quote(full_filename)

    ascii_clean = base_name.encode("ascii", "ignore").decode("ascii").strip(" ._")
    ascii_filename = f"{ascii_clean}.{ext}" if ascii_clean else f"media_download.{ext}"

    return f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'


class StorageBackend(ABC):
    """Abstract Base Class for file storage backends."""

    @abstractmethod
    def upload(self, local_path: str, object_key: str, content_type: Optional[str] = None) -> str:
        """
        Uploads or persists a media file to storage using a random object key.
        Returns the stored identifier/path.
        """
        pass

    @abstractmethod
    def delete(self, object_key: str) -> bool:
        """Deletes a file or object from storage."""
        pass

    @abstractmethod
    def exists(self, object_key: str) -> bool:
        """Checks if a file or object exists in storage."""
        pass

    @abstractmethod
    def get_file_size(self, object_key: str) -> Optional[int]:
        """Returns the file size in bytes if available."""
        pass

    @abstractmethod
    def get_presigned_url(
        self,
        object_key: str,
        filename: str,
        expiry_seconds: int = 1800,
    ) -> Optional[str]:
        """Generates a direct presigned download URL (R2 only, returns None for local)."""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        os.makedirs(self.storage_dir, exist_ok=True)

    def _resolve_path(self, object_key: str) -> str:
        if os.path.isabs(object_key):
            return object_key
        return os.path.join(self.storage_dir, object_key)

    def upload(self, local_path: str, object_key: str, content_type: Optional[str] = None) -> str:
        target_path = self._resolve_path(object_key)
        if os.path.abspath(local_path) != os.path.abspath(target_path):
            shutil.copy2(local_path, target_path)
        logger.info("LocalStorage: stored file at %s", target_path)
        return target_path

    def delete(self, object_key: str) -> bool:
        target_path = self._resolve_path(object_key)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                logger.info("LocalStorage: deleted file %s", target_path)
                return True
            except OSError as err:
                logger.warning("LocalStorage: failed to delete file %s: %s", target_path, str(err))
                return False
        return True

    def exists(self, object_key: str) -> bool:
        target_path = self._resolve_path(object_key)
        return os.path.exists(target_path)

    def get_file_size(self, object_key: str) -> Optional[int]:
        target_path = self._resolve_path(object_key)
        if os.path.exists(target_path):
            return os.path.getsize(target_path)
        return None

    def get_presigned_url(
        self,
        object_key: str,
        filename: str,
        expiry_seconds: int = 1800,
    ) -> Optional[str]:
        # LocalStorage files are served directly via FastAPI FileResponse
        return None


class R2Storage(StorageBackend):
    """
    Cloudflare R2 Object Storage Backend (S3-compatible API).
    Endpoint: https://<ACCOUNT_ID>.r2.cloudflarestorage.com
    Zero egress fee presigned URL distribution.
    """

    def __init__(
        self,
        account_id: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket: Optional[str] = None,
    ):
        import boto3
        from botocore.config import Config

        self.account_id = account_id if account_id is not None else settings.R2_ACCOUNT_ID
        self.access_key_id = access_key_id if access_key_id is not None else settings.R2_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key if secret_access_key is not None else settings.R2_SECRET_ACCESS_KEY
        self.bucket = bucket if bucket is not None else settings.R2_BUCKET

        if not self.account_id:
            raise ValueError("R2_ACCOUNT_ID must be configured for R2Storage.")
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError("R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY must be configured for R2Storage.")
        if not self.bucket:
            raise ValueError("R2_BUCKET must be configured for R2Storage.")

        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

        # S3 client with standard signature v4 and path-style addressing for Cloudflare R2
        boto_config = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            s3={"addressing_style": "path"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id.strip() if self.access_key_id else None,
            aws_secret_access_key=self.secret_access_key.strip() if self.secret_access_key else None,
            region_name="auto",
            config=boto_config,
        )

    def upload(self, local_path: str, object_key: str, content_type: Optional[str] = None) -> str:
        """
        Uploads local file to Cloudflare R2 under random object_key.
        Object keys MUST be random IDs (e.g. {job_id}.mp4), never the user's video title.
        """
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        else:
            file_ext = os.path.splitext(object_key)[1].lstrip(".")
            extra_args["ContentType"] = get_media_content_type(file_ext)

        logger.info("R2Storage: uploading %s to bucket %s with key %s", local_path, self.bucket, object_key)
        self.s3_client.upload_file(
            Filename=local_path,
            Bucket=self.bucket,
            Key=object_key,
            ExtraArgs=extra_args if extra_args else None,
        )
        return object_key

    def delete(self, object_key: str) -> bool:
        logger.info("R2Storage: deleting key %s from bucket %s", object_key, self.bucket)
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception as err:
            logger.warning("R2Storage: delete failed for %s: %s", object_key, str(err))
            return False

    def exists(self, object_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception:
            return False

    def get_file_size(self, object_key: str) -> Optional[int]:
        try:
            resp = self.s3_client.head_object(Bucket=self.bucket, Key=object_key)
            return resp.get("ContentLength")
        except Exception:
            return None

    def get_presigned_url(
        self,
        object_key: str,
        filename: str,
        expiry_seconds: int = 1800,
    ) -> Optional[str]:
        """
        Generates an expiring presigned S3 URL with RFC 5987 / RFC 6266 Content-Disposition
        so the browser saves the file with the sanitized video title.
        """
        file_ext = os.path.splitext(object_key)[1].lstrip(".")
        content_disposition = build_content_disposition(filename, file_ext)

        params = {
            "Bucket": self.bucket,
            "Key": object_key,
            "ResponseContentDisposition": content_disposition,
        }

        url = self.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=expiry_seconds,
        )
        return url


def get_storage(backend: Optional[str] = None) -> StorageBackend:
    """
    Factory function returning the configured StorageBackend implementation.
    Selects between LocalStorage (default) and R2Storage based on STORAGE_BACKEND env var.
    """
    selected = (backend or settings.STORAGE_BACKEND or "local").lower().strip()
    if selected == "r2":
        return R2Storage()
    return LocalStorage()
