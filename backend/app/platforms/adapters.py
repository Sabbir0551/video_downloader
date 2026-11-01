import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.core.errors import AppError, UnsupportedUrlError

logger = logging.getLogger("anystream.adapters")


class BasePlatformAdapter:
    """Base class for platform-specific extraction and download behaviors."""

    platform_id: str = "generic"

    def pre_validate_url(self, url: str) -> bool:
        """Validate URL syntax specific to this platform."""
        return True

    def canonicalize_url(self, url: str) -> str:
        """Normalize URL removing tracking codes and query garbage."""
        return url

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        """Inject platform-tailored yt-dlp parameters."""
        return {}

    def map_error(self, err: Exception) -> Optional[AppError]:
        """Custom platform error mapping."""
        return None


class YouTubeAdapter(BasePlatformAdapter):
    platform_id = "youtube"

    def canonicalize_url(self, url: str) -> str:
        # Normalize shorts or youtu.be links
        parsed = urlparse(url)
        path = parsed.path
        if "/shorts/" in path:
            video_id = path.split("/shorts/")[1].split("/")[0].split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return url

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        return {
            "format_sort": ["res", "fps", "hdr:12", "vcodec:av01", "vcodec:vp09", "channels", "acodec", "size"],
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                    "skip": ["hls"],
                }
            },
        }


class TikTokAdapter(BasePlatformAdapter):
    platform_id = "tiktok"

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        # Prefer watermark-free direct CDN stream
        return {
            "extractor_args": {
                "tiktok": {
                    "app_version": ["31.5.3"],
                }
            },
            "http_headers": {
                "Referer": "https://www.tiktok.com/",
            },
        }


class InstagramAdapter(BasePlatformAdapter):
    platform_id = "instagram"

    def canonicalize_url(self, url: str) -> str:
        # Strip tracking queries
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return f"https://www.instagram.com{path}/"

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        return {
            "http_headers": {
                "Referer": "https://www.instagram.com/",
            },
        }


class TwitterAdapter(BasePlatformAdapter):
    platform_id = "twitter"

    def canonicalize_url(self, url: str) -> str:
        # Convert twitter.com or x.com to uniform format
        parsed = urlparse(url)
        path = parsed.path
        m = re.search(r"/status/(\d+)", path)
        if m:
            status_id = m.group(1)
            return f"https://x.com/i/status/{status_id}"
        return url

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        return {
            "format_sort": ["res", "vcodec", "acodec", "size"],
        }


class RedditAdapter(BasePlatformAdapter):
    platform_id = "reddit"

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        # Ensure separate DASH audio and video fragments merge cleanly
        return {
            "merge_output_format": "mp4",
        }


# Adapter Registry Map
ADAPTER_MAP = {
    "youtube": YouTubeAdapter(),
    "tiktok": TikTokAdapter(),
    "instagram": InstagramAdapter(),
    "twitter": TwitterAdapter(),
    "reddit": RedditAdapter(),
}


def get_platform_adapter(platform_id: Optional[str]) -> BasePlatformAdapter:
    """Returns platform adapter instance or default fallback."""
    if platform_id and platform_id in ADAPTER_MAP:
        return ADAPTER_MAP[platform_id]
    return BasePlatformAdapter()
