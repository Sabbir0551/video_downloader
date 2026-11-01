import html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx

from app.core.ssrf import safe_network_guard

logger = logging.getLogger("anystream.embed_resolver")

DIRECT_MEDIA_EXTENSIONS = {
    "mp4", "m4v", "webm", "mkv", "mov", "avi", "flv", "wmv",
    "mp3", "m4a", "aac", "ogg", "opus", "flac", "wav"
}

KNOWN_EMBED_PATTERNS = [
    re.compile(r"https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)"),
    re.compile(r"https?://player\.vimeo\.com/video/(\d+)"),
    re.compile(r"https?://(?:www\.)?loom\.com/share/([a-zA-Z0-9]+)"),
    re.compile(r"https?://iframe\.videodelivery\.net/([a-zA-Z0-9]+)"),
    re.compile(r"https?://(?:www\.)?streamable\.com/(?:e/)?([a-zA-Z0-9]+)"),
    re.compile(r"https?://(?:www\.)?dailymotion\.com/embed/video/([a-zA-Z0-9]+)"),
    re.compile(r"https?://fast\.wistia\.(?:net|com)/embed/iframe/([a-zA-Z0-9]+)"),
]


def is_direct_media_url(url: str) -> bool:
    """Checks if the URL points directly to an audio or video file."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    ext = path.split(".")[-1] if "." in path else ""
    return ext in DIRECT_MEDIA_EXTENSIONS


def build_direct_media_info(
    url: str,
    title: Optional[str] = None,
    thumbnail: Optional[str] = None,
) -> Dict[str, Any]:
    """Constructs a yt-dlp compliant info_dict for direct media URLs."""
    parsed = urlparse(url)
    path = parsed.path
    filename = path.split("/")[-1].split("?")[0] if "/" in path else "media"
    ext = filename.split(".")[-1].lower() if "." in filename else "mp4"
    if ext not in DIRECT_MEDIA_EXTENSIONS:
        ext = "mp4"

    is_audio = ext in {"mp3", "m4a", "aac", "ogg", "opus", "flac", "wav"}
    clean_title = title or filename.rsplit(".", 1)[0] or "Direct Media"

    vcodec = "none" if is_audio else ("h264" if ext in {"mp4", "mov"} else "vp9")
    acodec = "mp3" if ext == "mp3" else ("aac" if ext in {"mp4", "mov", "m4a"} else "opus")

    return {
        "id": hashlib_id(url),
        "title": clean_title,
        "url": url,
        "webpage_url": url,
        "thumbnail": thumbnail or "",
        "extractor": "generic:direct",
        "extractor_key": "DirectMedia",
        "duration": 0,
        "formats": [
            {
                "format_id": "direct",
                "url": url,
                "ext": ext,
                "vcodec": vcodec,
                "acodec": acodec,
                "height": None if is_audio else 1080,
                "width": None if is_audio else 1920,
                "fps": None if is_audio else 30,
                "format_note": f"Direct {ext.upper()} stream",
            }
        ],
    }


def hashlib_id(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def extract_embed_or_media_from_html(html_text: str, base_url: str) -> Optional[Dict[str, Any]]:
    """
    Scans HTML text for OpenGraph video, Twitter Player, HTML5 <video>/<audio>,
    or known third-party embed iframes.
    """
    # 1. Check for iframe embeds of supported services (YouTube, Vimeo, Loom, Cloudflare, etc.)
    iframe_matches = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    for iframe_src in iframe_matches:
        full_iframe_url = urljoin(base_url, html.unescape(iframe_src))
        for pattern in KNOWN_EMBED_PATTERNS:
            if pattern.search(full_iframe_url):
                logger.info("Found supported iframe embed: %s", full_iframe_url)
                return {
                    "type": "resolved_url",
                    "url": full_iframe_url,
                }

    # 2. Check for OpenGraph or Twitter video meta tags (both property-first and content-first)
    meta_patterns = [
        r'<meta[^>]+(?:property|name)=["\']og:video:secure_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+(?:property|name)=["\']og:video:url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+(?:property|name)=["\']og:video["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+(?:property|name)=["\']twitter:player:stream["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+(?:property|name)=["\']twitter:player["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:video:secure_url["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:video:url["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:video["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']twitter:player:stream["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']twitter:player["\']',
    ]
    for pattern in meta_patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            media_src = urljoin(base_url, html.unescape(match.group(1)))
            if is_direct_media_url(media_src) or any(p.search(media_src) for p in KNOWN_EMBED_PATTERNS):
                logger.info("Found OpenGraph/Twitter video: %s", media_src)
                return {
                    "type": "resolved_url",
                    "url": media_src,
                }

    # 3. Check for HTML5 <video> / <source> direct streams
    video_matches = re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    video_matches += re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    for v_src in video_matches:
        full_video_url = urljoin(base_url, html.unescape(v_src))
        if is_direct_media_url(full_video_url):
            logger.info("Found HTML5 direct video stream: %s", full_video_url)
            return {
                "type": "direct_media",
                "url": full_video_url,
            }

    # 4. Check for HTML5 <audio> direct streams
    audio_matches = re.findall(r'<audio[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    for a_src in audio_matches:
        full_audio_url = urljoin(base_url, html.unescape(a_src))
        if is_direct_media_url(full_audio_url):
            logger.info("Found HTML5 direct audio stream: %s", full_audio_url)
            return {
                "type": "direct_media",
                "url": full_audio_url,
            }

    return None


def fetch_and_resolve_page_media(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """
    Safely fetches the given URL and attempts to extract embedded video or direct media.
    Protected with safe_network_guard() against SSRF.
    """
    if is_direct_media_url(url):
        return build_direct_media_info(url)

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        req_headers.update(headers)

    try:
        with safe_network_guard():
            with httpx.Client(timeout=8.0, follow_redirects=True, headers=req_headers) as client:
                resp = client.get(url)
                content_type = resp.headers.get("content-type", "").lower()

                # If content-type is directly video or audio
                if any(t in content_type for t in ("video/", "audio/", "application/vnd.apple.mpegurl", "application/x-mpegurl")):
                    return build_direct_media_info(str(resp.url))

                # If HTML, limit read to first 2MB
                html_text = resp.text[:2 * 1024 * 1024]
                parsed_res = extract_embed_or_media_from_html(html_text, str(resp.url))
                if not parsed_res:
                    return None

                # If direct media or resolved direct URL
                if parsed_res.get("type") in ("direct_media", "resolved_url") and is_direct_media_url(parsed_res.get("url", "")):
                    # Extract page title from og:title or <title>
                    title_match = re.search(r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                    if not title_match:
                        title_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:title["\']', html_text, re.IGNORECASE)
                    if not title_match:
                        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_text, re.IGNORECASE)

                    page_title = html.unescape(title_match.group(1)).strip() if title_match else None

                    # Extract thumbnail from og:image
                    thumb_match = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:image:secure_url|og:image:url|og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                    if not thumb_match:
                        thumb_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image:secure_url|og:image:url|og:image|twitter:image)["\']', html_text, re.IGNORECASE)
                    thumbnail = html.unescape(thumb_match.group(1)) if thumb_match else None

                    return build_direct_media_info(parsed_res["url"], title=page_title, thumbnail=thumbnail)

                return parsed_res
    except Exception as e:
        logger.debug("Failed to resolve embed for %s: %s", url, str(e))
        return None
