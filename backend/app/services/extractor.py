import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import redis
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from app.core.config import settings
from app.core.errors import (
    AppError,
    DRMProtectedError,
    MediaTooLargeError,
    RateLimitExceededError,
    UnsupportedUrlError,
)
from app.core.security import normalize_video_url, sanitize_display_title, sanitize_filename
from app.core.ssrf import safe_network_guard
from app.schemas.extract import FormatOption, MediaInfoResponse

logger = logging.getLogger("anystream.extractor")

# Redis connection for caching extraction metadata
try:
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )
except Exception:
    redis_client = None


class SilentLogger:
    """Disables noisy yt-dlp stdout logging to preserve clean structured logs."""
    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


def get_ydl_options() -> Dict[str, Any]:
    """Default secure configuration dictionary for yt_dlp.YoutubeDL."""
    return {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "socket_timeout": 30,
        "noplaylist": True,
        "no_color": True,
        "ignoreerrors": False,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "js_runtimes": {"node": {}},
        "logger": SilentLogger(),
    }


def map_ytdlp_error(err: Exception) -> AppError:
    """Maps raw yt-dlp exceptions to user-friendly, security-safe domain errors."""
    err_msg = str(err)
    err_lower = err_msg.lower()

    if "drm" in err_lower or "encrypted" in err_lower or "widevine" in err_lower:
        return DRMProtectedError("This media stream is DRM-protected and cannot be downloaded.")

    if "private video" in err_lower or "sign in" in err_lower or "requires authentication" in err_lower:
        return UnsupportedUrlError("This video is private, restricted, or requires an authenticated account.")

    if "unavailable" in err_lower or "removed" in err_lower or "does not exist" in err_lower:
        return UnsupportedUrlError("This video is unavailable, deleted, or was removed by the creator.")

    if "geo-restricted" in err_lower or "not available in your country" in err_lower:
        return UnsupportedUrlError("This video is geo-restricted and not accessible in this server's region.")

    if "live stream" in err_lower or "is a live stream" in err_lower:
        return UnsupportedUrlError("Active livestreams cannot be downloaded until broadcasting has ended.")

    if "http error 429" in err_lower or "too many requests" in err_lower:
        return RateLimitExceededError("The upstream video provider is temporarily rate-limiting requests. Please try again later.")

    if "unsupported url" in err_lower or "is not a valid url" in err_lower:
        return UnsupportedUrlError("This URL or media host is not currently supported.")

    if "timed out" in err_lower or "timeout" in err_lower or "connection refused" in err_lower:
        return UnsupportedUrlError("Connection to the media host timed out. Please try again.")

    if "signature" in err_lower or "extractor" in err_lower or "nsig" in err_lower:
        return AppError(
            status_code=502,
            error_code="UPSTREAM_EXTRACTOR_DEPRECATED",
            message="Upstream video provider updated their format. System is queued for extractor update.",
        )

    logger.warning("Unmapped yt-dlp extraction error: %s", err_msg)
    return UnsupportedUrlError("Unable to retrieve information for this URL. Please verify the link is publicly accessible.")


def normalize_formats(formats: List[Dict[str, Any]], duration: int) -> List[FormatOption]:
    """
    Parses and deduplicates raw stream formats into a clean, intuitive quality picker:
    - High-quality video options (e.g. 1080p, 720p, 480p, 360p, 240p, 144p).
    - Audio-only options (e.g. M4A and universal MP3).
    """
    if not formats:
        return []

    # 1. Identify best audio stream for multiplexing
    best_audio: Optional[Dict[str, Any]] = None
    best_audio_abr: float = 0.0

    for fmt in formats:
        acodec = fmt.get("acodec", "none")
        vcodec = fmt.get("vcodec", "none")
        if acodec != "none" and vcodec == "none":
            abr = float(fmt.get("abr") or fmt.get("tbr") or 0.0)
            if abr > best_audio_abr:
                best_audio_abr = abr
                best_audio = fmt

    best_audio_id = best_audio.get("format_id") if best_audio else None
    best_audio_size = (
        (best_audio.get("filesize") or best_audio.get("filesize_approx"))
        if best_audio else None
    )
    if not best_audio_size and best_audio_abr and duration:
        # Estimate audio bytes: (kbps * 1000 / 8) * duration
        best_audio_size = int((best_audio_abr * 125) * duration)

    # 2. Extract and group video streams by vertical resolution
    video_resolutions: Dict[int, Dict[str, Any]] = {}

    for fmt in formats:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec", "none")
        ext = fmt.get("ext", "mp4")

        # Ignore audio-only formats in video pass
        if vcodec == "none" or not height or height < 144:
            continue

        # Skip storyboards and low-quality manifests
        protocol = fmt.get("protocol", "")
        if "mhtml" in protocol or ext in ("mhtml",):
            continue

        existing = video_resolutions.get(height)
        fps = float(fmt.get("fps") or 30.0)
        tbr = float(fmt.get("tbr") or fmt.get("vbr") or 0.0)

        # Prefer MP4 over WebM for wider device compatibility, then higher bitrate/fps
        is_preferred = False
        if not existing:
            is_preferred = True
        else:
            existing_ext = existing.get("ext", "")
            existing_tbr = float(existing.get("tbr") or existing.get("vbr") or 0.0)
            if existing_ext != "mp4" and ext == "mp4":
                is_preferred = True
            elif ext == existing_ext and tbr > existing_tbr:
                is_preferred = True

        if is_preferred:
            video_resolutions[height] = fmt

    format_options: List[FormatOption] = []

    # 3. Build sorted video FormatOptions (descending height)
    sorted_heights = sorted(video_resolutions.keys(), reverse=True)
    for height in sorted_heights:
        raw_fmt = video_resolutions[height]
        v_id = raw_fmt.get("format_id", "")
        fps = float(raw_fmt.get("fps") or 30.0)
        acodec = raw_fmt.get("acodec", "none")
        ext = raw_fmt.get("ext", "mp4")

        # Label quality
        if height >= 2160:
            note = f"4K ({height}p)"
        elif height >= 1440:
            note = f"2K ({height}p)"
        elif height >= 1080:
            note = f"1080p (Full HD)"
        elif height >= 720:
            note = f"720p (HD)"
        elif height >= 480:
            note = f"480p (SD)"
        else:
            note = f"{height}p"

        if fps >= 50:
            note = f"{note} {int(fps)}fps"

        # Calculate estimated size
        v_size = raw_fmt.get("filesize") or raw_fmt.get("filesize_approx")
        if not v_size:
            v_tbr = float(raw_fmt.get("tbr") or raw_fmt.get("vbr") or 0.0)
            if v_tbr and duration:
                v_size = int((v_tbr * 125) * duration)

        total_size = v_size
        # If video has no audio, multiplex with best audio
        if acodec == "none" and best_audio_id:
            combined_format_id = f"{v_id}+{best_audio_id}"
            if v_size and best_audio_size:
                total_size = v_size + best_audio_size
        else:
            combined_format_id = v_id

        format_options.append(
            FormatOption(
                format_id=combined_format_id,
                resolution=f"{height}p",
                height=height,
                fps=fps,
                ext="mp4",  # Worker remuxes to mp4 for universal playback
                format_note=note,
                filesize_approx=total_size,
                is_audio_only=False,
                abr=best_audio_abr if acodec == "none" else raw_fmt.get("abr"),
            )
        )

    # 4. Add audio-only options
    if best_audio:
        # M4A Audio
        format_options.append(
            FormatOption(
                format_id=best_audio.get("format_id", "bestaudio"),
                resolution=None,
                height=None,
                fps=None,
                ext="m4a",
                format_note=f"Audio Only ({int(best_audio_abr)} kbps M4A)" if best_audio_abr else "Audio Only (M4A)",
                filesize_approx=best_audio_size,
                is_audio_only=True,
                abr=best_audio_abr,
            )
        )
        # MP3 Audio
        format_options.append(
            FormatOption(
                format_id=f"{best_audio.get('format_id', 'bestaudio')}+mp3",
                resolution=None,
                height=None,
                fps=None,
                ext="mp3",
                format_note=f"Audio Only (MP3 High Quality)",
                filesize_approx=best_audio_size,
                is_audio_only=True,
                abr=best_audio_abr,
            )
        )

    return format_options


def extract_media_info(url: str, bypass_cache: bool = False) -> MediaInfoResponse:
    """
    Synchronously extracts media metadata using yt-dlp in Python library mode.
    Caches successful extractions for CACHE_TTL_SECONDS and errors for CACHE_ERROR_TTL_SECONDS.

    Args:
        url: Validated, SSRF-checked public media URL.
        bypass_cache: Set True to force fresh upstream extraction.

    Returns:
        MediaInfoResponse containing clean title, thumbnail, duration, and format options.

    Raises:
        AppError: Mapped user-safe domain exception.
    """
    canonical_url, _ = normalize_video_url(url)
    url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    cache_key = f"cache:info:{url_hash}"
    err_cache_key = f"cache:info:err:{url_hash}"

    # 1. Check Redis cache
    if not bypass_cache and redis_client:
        try:
            cached_json = redis_client.get(cache_key)
            if cached_json:
                logger.info("Cache HIT for media URL [%s]", canonical_url)
                try:
                    from app.core.metrics import record_cache_hit
                    record_cache_hit()
                except Exception:
                    pass
                return MediaInfoResponse.model_validate_json(cached_json)

            cached_err = redis_client.get(err_cache_key)
            if cached_err:
                err_data = json.loads(cached_err)
                logger.info("Cache HIT (negative error cache) for media URL [%s]", canonical_url)
                try:
                    from app.core.metrics import record_cache_hit
                    record_cache_hit()
                except Exception:
                    pass
                raise AppError(
                    status_code=err_data.get("status_code", 400),
                    error_code=err_data.get("error_code", "UNSUPPORTED_URL_OR_PLATFORM"),
                    message=err_data.get("message", "Unable to extract media information."),
                )
            try:
                from app.core.metrics import record_cache_miss
                record_cache_miss()
            except Exception:
                pass
        except AppError:
            raise
        except Exception as e:
            logger.debug("Redis cache read failed: %s", str(e))

    ydl_opts = get_ydl_options()

    try:
        with safe_network_guard():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
    except Exception as err:
        app_err = map_ytdlp_error(err)
        # Cache negative error for short TTL
        if redis_client:
            try:
                redis_client.setex(
                    err_cache_key,
                    settings.CACHE_ERROR_TTL_SECONDS,
                    json.dumps({
                        "status_code": app_err.status_code,
                        "error_code": app_err.error_code,
                        "message": app_err.message,
                    }),
                )
            except Exception:
                pass
        raise app_err

    if not info_dict:
        raise UnsupportedUrlError("Could not retrieve media details from this URL.")

    # Check for DRM flags
    if info_dict.get("has_drm") or info_dict.get("_drm"):
        raise DRMProtectedError("This media stream is DRM-protected and cannot be downloaded.")

    # Check for active livestreams
    if info_dict.get("is_live"):
        raise UnsupportedUrlError("Active livestreams cannot be downloaded until broadcasting completes.")

    # Duration validation
    duration = int(info_dict.get("duration") or 0)
    if duration > settings.MAX_VIDEO_DURATION_SECONDS:
        raise MediaTooLargeError(
            f"The video duration ({duration // 60} minutes) exceeds the platform maximum of {settings.MAX_VIDEO_DURATION_SECONDS // 60} minutes."
        )

    # Sanitize human-readable title
    raw_title = info_dict.get("title") or "Untitled Media"
    clean_title = sanitize_display_title(raw_title)

    # Thumbnail resolution
    thumbnails = info_dict.get("thumbnails") or []
    thumbnail_url = info_dict.get("thumbnail") or ""
    if not thumbnail_url and thumbnails:
        thumbnail_url = thumbnails[-1].get("url", "")

    # Clean formats
    raw_formats = info_dict.get("formats") or []
    clean_formats = normalize_formats(raw_formats, duration)

    result = MediaInfoResponse(
        id=str(info_dict.get("id") or "media"),
        title=clean_title,
        url=str(info_dict.get("webpage_url") or url),
        thumbnail_url=thumbnail_url,
        duration=duration,
        uploader=info_dict.get("uploader") or info_dict.get("channel"),
        is_live=bool(info_dict.get("is_live")),
        formats=clean_formats,
    )

    # Store successful extraction in Redis
    if redis_client:
        try:
            redis_client.setex(cache_key, settings.CACHE_TTL_SECONDS, result.model_dump_json())
            logger.info("Stored media info in Redis cache with TTL %ds for [%s]", settings.CACHE_TTL_SECONDS, canonical_url)
        except Exception as e:
            logger.debug("Failed to write to Redis cache: %s", str(e))

    return result
