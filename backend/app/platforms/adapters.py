import html
import json
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import httpx

from app.core.errors import AppError, UnsupportedUrlError
from app.core.ssrf import safe_network_guard
from app.services.embed_resolver import (
    build_direct_media_info,
    fetch_and_resolve_page_media,
    is_direct_media_url,
)

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

    def extract_custom_media(self, url: str) -> Optional[Dict[str, Any]]:
        """Optional custom extraction fallback when yt-dlp is insufficient."""
        return None

    def map_error(self, err: Exception) -> Optional[AppError]:
        """Custom platform error mapping."""
        return None


class YouTubeAdapter(BasePlatformAdapter):
    platform_id = "youtube"

    def canonicalize_url(self, url: str) -> str:
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
        return {
            "merge_output_format": "mp4",
        }


class TelegramAdapter(BasePlatformAdapter):
    """
    Adapter for public Telegram channel posts (t.me/{channel}/{msg_id}).
    Canonicalizes /s/ URLs to match yt-dlp TelegramEmbedIE and provides
    HTML fallback parsing for public channel web views.
    """
    platform_id = "telegram"

    def canonicalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = path.split("/")

        # Handle t.me/s/{channel}/{id} -> t.me/{channel}/{id}
        if len(parts) >= 3 and parts[0] == "s":
            channel, msg_id = parts[1], parts[2]
            return f"https://t.me/{channel}/{msg_id}"
        elif len(parts) >= 2 and parts[1].isdigit():
            channel, msg_id = parts[0], parts[1]
            return f"https://t.me/{channel}/{msg_id}"
        return url

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        return {
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            }
        }

    def extract_custom_media(self, url: str) -> Optional[Dict[str, Any]]:
        """Fallback parser that reads Telegram public web view (t.me/s/{channel}/{msg_id})."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]
        if parts and parts[0] == "s":
            parts = parts[1:]
        if len(parts) < 2 or not parts[1].isdigit():
            return None

        channel, msg_id = parts[0], parts[1]
        web_preview_url = f"https://t.me/s/{channel}/{msg_id}"

        try:
            with safe_network_guard():
                with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                    resp = client.get(web_preview_url)
                    if resp.status_code != 200:
                        return None
                    html_content = resp.text

                    # Search for video source
                    video_match = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
                    if video_match:
                        video_url = html.unescape(video_match.group(1))
                        # Title
                        title = f"Telegram post @{channel}/{msg_id}"
                        text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', html_content, re.DOTALL)
                        if text_match:
                            clean_text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()
                            if clean_text:
                                title = clean_text[:80]

                        return {
                            "id": f"tg_{channel}_{msg_id}",
                            "title": title,
                            "url": video_url,
                            "webpage_url": url,
                            "extractor": "telegram:web",
                            "extractor_key": "Telegram",
                            "duration": 0,
                            "formats": [
                                {
                                    "format_id": "telegram_video",
                                    "url": video_url,
                                    "ext": "mp4",
                                    "vcodec": "h264",
                                    "acodec": "aac",
                                    "height": 720,
                                    "format_note": "Telegram Public Video",
                                }
                            ],
                        }
        except Exception as e:
            logger.debug("Telegram custom extraction failed: %s", str(e))
        return None


class XiaohongshuAdapter(BasePlatformAdapter):
    """
    Adapter for Xiaohongshu (RedNote).
    Follows short links (xhslink.com), normalizes to www.xiaohongshu.com,
    and extracts public video state via window.__INITIAL_STATE__.
    """
    platform_id = "xiaohongshu"

    def canonicalize_url(self, url: str) -> str:
        # Resolve xhslink.com redirect if necessary
        if "xhslink.com" in url:
            try:
                with safe_network_guard():
                    with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                        resp = client.head(url)
                        url = str(resp.url)
            except Exception:
                pass

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname == "xiaohongshu.com":
            hostname = "www.xiaohongshu.com"

        clean_path = parsed.path
        return urlunparse((parsed.scheme or "https", hostname, clean_path, "", "", ""))

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        return {
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                "Referer": "https://www.xiaohongshu.com/",
            }
        }

    def extract_custom_media(self, url: str) -> Optional[Dict[str, Any]]:
        """Parses window.__INITIAL_STATE__ for non-watermarked MP4 streams."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Referer": "https://www.xiaohongshu.com/",
            }
            with safe_network_guard():
                with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        return None

                    html_content = resp.text
                    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?</script>', html_content, re.DOTALL)
                    if not match:
                        match = re.search(r'window\.__INITIAL_SSR_STATE__\s*=\s*(\{.*?\});?</script>', html_content, re.DOTALL)

                    if not match:
                        return None

                    # Extract video URL from json
                    data = json.loads(match.group(1))
                    note_data = (
                        data.get("note", {}).get("noteDetailMap", {}) or
                        data.get("noteData", {})
                    )
                    # Search recursively for video masterUrl
                    video_url = None
                    title = "Xiaohongshu Note"
                    if isinstance(note_data, dict):
                        for k, v in note_data.items():
                            if isinstance(v, dict) and "note" in v:
                                inner_note = v["note"]
                                title = inner_note.get("title") or inner_note.get("desc") or title
                                video_info = inner_note.get("video", {})
                                stream = video_info.get("media", {}).get("stream", {})
                                for codec_key in ("h264", "h265", "av1"):
                                    streams = stream.get(codec_key, [])
                                    if streams and isinstance(streams, list):
                                        video_url = streams[0].get("masterUrl")
                                        if video_url:
                                            break
                            if video_url:
                                break

                    if video_url:
                        return {
                            "id": hashlib_id(url),
                            "title": title[:100],
                            "url": video_url,
                            "webpage_url": url,
                            "extractor": "xiaohongshu:web",
                            "extractor_key": "XiaoHongShu",
                            "duration": 0,
                            "formats": [
                                {
                                    "format_id": "xhs_best",
                                    "url": video_url,
                                    "ext": "mp4",
                                    "vcodec": "h264",
                                    "acodec": "aac",
                                    "height": 1080,
                                    "format_note": "Xiaohongshu HD Video",
                                }
                            ],
                        }
        except Exception as e:
            logger.debug("Xiaohongshu custom extraction failed: %s", str(e))
        return None


class SubstackAdapter(BasePlatformAdapter):
    """
    Adapter for Substack posts and podcasts.
    Extracts podcast audio files and embedded videos.
    """
    platform_id = "substack"

    def canonicalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        # Strip tracking params
        return urlunparse((parsed.scheme, parsed.hostname, parsed.path, "", "", ""))

    def get_ydl_options(self, url: str) -> Dict[str, Any]:
        return {
            "http_headers": {
                "Referer": "https://substack.com/",
            }
        }

    def extract_custom_media(self, url: str) -> Optional[Dict[str, Any]]:
        """Parses Substack podcast audio enclosure or embedded video."""
        try:
            with safe_network_guard():
                with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        return None

                    html_content = resp.text

                    # Check for podcast audio enclosure
                    audio_match = re.search(r'<audio[^>]+src=["\']([^"\']+\.mp3[^"\']*)["\']', html_content, re.IGNORECASE)
                    if not audio_match:
                        audio_match = re.search(r'data-attrs=["\'][^"\']*?(https?://[^"\']+\.mp3)[^"\']*?["\']', html_content, re.IGNORECASE)

                    if audio_match:
                        audio_url = html.unescape(audio_match.group(1))
                        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL)
                        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "Substack Podcast"

                        return {
                            "id": hashlib_id(url),
                            "title": title,
                            "url": audio_url,
                            "webpage_url": url,
                            "extractor": "substack:audio",
                            "extractor_key": "Substack",
                            "duration": 0,
                            "formats": [
                                {
                                    "format_id": "substack_audio",
                                    "url": audio_url,
                                    "ext": "mp3",
                                    "vcodec": "none",
                                    "acodec": "mp3",
                                    "abr": 192.0,
                                    "format_note": "Substack Podcast Audio (MP3)",
                                }
                            ],
                        }
        except Exception as e:
            logger.debug("Substack custom extraction failed: %s", str(e))
        return None


class DirectEmbedAdapter(BasePlatformAdapter):
    """
    Adapter for GitHub, Discord CDN, Behance, Medium, Dev.to, Product Hunt, etc.
    Scans for direct media streams or nested video embeds.
    """
    platform_id = "embed_or_direct"

    def extract_custom_media(self, url: str) -> Optional[Dict[str, Any]]:
        return fetch_and_resolve_page_media(url)


def hashlib_id(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# Adapter Registry Map
ADAPTER_MAP: Dict[str, BasePlatformAdapter] = {
    "youtube": YouTubeAdapter(),
    "tiktok": TikTokAdapter(),
    "instagram": InstagramAdapter(),
    "twitter": TwitterAdapter(),
    "reddit": RedditAdapter(),
    "telegram": TelegramAdapter(),
    "xiaohongshu": XiaohongshuAdapter(),
    "substack": SubstackAdapter(),
    "discord": DirectEmbedAdapter(),
    "github": DirectEmbedAdapter(),
    "gitlab": DirectEmbedAdapter(),
    "behance": DirectEmbedAdapter(),
    "medium": DirectEmbedAdapter(),
    "dev_to": DirectEmbedAdapter(),
    "hashnode": DirectEmbedAdapter(),
    "producthunt": DirectEmbedAdapter(),
    "ask_fm": DirectEmbedAdapter(),
    "douban": DirectEmbedAdapter(),
    "naver_band": DirectEmbedAdapter(),
    "ko_fi": DirectEmbedAdapter(),
    "diaspora": DirectEmbedAdapter(),
    "vero": DirectEmbedAdapter(),
    "pillowfort": DirectEmbedAdapter(),
}


def get_platform_adapter(platform_id: Optional[str]) -> BasePlatformAdapter:
    """Returns platform adapter instance or default fallback."""
    if platform_id and platform_id in ADAPTER_MAP:
        return ADAPTER_MAP[platform_id]
    return BasePlatformAdapter()
