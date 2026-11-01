import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import redis
import yt_dlp
from yt_dlp.utils import DownloadError

from app.core.config import settings
from app.core.errors import (
    AppError,
    DRMProtectedError,
    MediaTooLargeError,
    RateLimitExceededError,
    UnsupportedUrlError,
)
from app.core.ssrf import safe_network_guard
from app.platforms.adapters import get_platform_adapter
from app.platforms.registry import get_platform_registry
from app.schemas.extract import FormatOption, MediaInfoResponse

logger = logging.getLogger("anystream.extractor")

# Optional Redis connection for info caching
redis_client: Optional[redis.Redis] = None
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    logger.warning("Redis not available for info caching: %s", str(e))


class SilentLogger:
    """Disables noisy yt-dlp standard logging while retaining structured error traces."""

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        logger.error("yt-dlp core error: %s", msg)


def sanitize_display_title(title: Optional[str]) -> str:
    """Removes terminal control codes, excessive whitespace, and dangerous HTML tags."""
    if not title:
        return "Untitled Media"
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", "", title)
    # Strip non-printable / control characters
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean)
    clean = " ".join(clean.split())
    return clean[:200] if clean else "Untitled Media"


def normalize_video_url(raw_url: str) -> tuple[str, Optional[str]]:
    """
    Normalizes a video URL:
    - Strips tracking / analytics query parameters (utm_*, fbclid, si, etc.).
    - Extracts canonical video ID where feasible.
    """
    parsed = urlparse(raw_url)
    tracking_prefixes = ("utm_", "fbclid", "gclid", "msclkid", "si", "ref", "feature")

    # Filter query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered_params = {
        k: v for k, v in query_params.items()
        if not any(k.lower().startswith(prefix) for prefix in tracking_prefixes)
    }

    canonical_id: Optional[str] = None
    hostname = (parsed.hostname or "").lower()

    # YouTube: preserve 'v' parameter
    if "youtube.com" in hostname:
        if "v" in filtered_params:
            canonical_id = filtered_params["v"][0]
            filtered_params = {"v": [canonical_id]}
    elif "youtu.be" in hostname:
        path_parts = parsed.path.strip("/").split("/")
        if path_parts and path_parts[0]:
            canonical_id = path_parts[0]

    # Reconstruct normalized URL
    clean_query = urlencode(filtered_params, doseq=True)
    canonical_url = urlunparse((
        parsed.scheme.lower(),
        hostname,
        parsed.path,
        parsed.params,
        clean_query,
        "",  # Strip fragment
    ))

    return canonical_url, canonical_id


def get_ydl_options() -> Dict[str, Any]:
    """Returns hardened default options for yt-dlp metadata extraction."""
    return {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "socket_timeout": 30,
        "retries": 3,
        "noplaylist": True,
        "no_color": True,
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
        return AppError(
            status_code=504,
            error_code="UPSTREAM_TIMEOUT",
            message="Connection to the media host timed out. Please try again.",
        )

    if "s3" in err_lower or "botocore" in err_lower or "boto3" in err_lower or "bucket" in err_lower:
        return AppError(
            status_code=500,
            error_code="STORAGE_ERROR",
            message="Storage backend encountered an error while storing media.",
        )

    if "signature" in err_lower or "extractor" in err_lower or "nsig" in err_lower:
        return AppError(
            status_code=502,
            error_code="UPSTREAM_EXTRACTOR_DEPRECATED",
            message="Upstream video provider updated their format. System is queued for extractor update.",
        )

    logger.warning("Unmapped yt-dlp extraction error: %s", err_msg)
    return UnsupportedUrlError("Unable to retrieve information for this URL. Please verify the link is publicly accessible.")


def normalize_formats(
    formats: List[Dict[str, Any]],
    duration: int,
    url: Optional[str] = None,
) -> List[FormatOption]:
    """
    Best-quality pipeline format normalizer:
    1. Identifies best audio stream (highest bitrate Opus/AAC) and best AAC audio (for universal MP4).
    2. Groups video streams by vertical resolution (up to 4K / 8K).
    3. Detects HDR, codecs, fps, and estimated byte size.
    4. Provides two modes per resolution:
       - 'original': Best fidelity native stream (AV1/VP9/H.264, container mkv/webm/mp4).
       - 'compatible_mp4': Universal playback (H.264/AAC in MP4).
    5. Applies per-platform quality caps from registry.
    6. Audio-only options: best original (M4A/Opus) and MP3 (320kbps / 192kbps).
    """
    if not formats:
        return []

    # 1. Identify best audio streams
    best_audio: Optional[Dict[str, Any]] = None
    best_audio_abr: float = 0.0

    best_aac_audio: Optional[Dict[str, Any]] = None
    best_aac_abr: float = 0.0

    for fmt in formats:
        acodec = fmt.get("acodec", "none") or "none"
        vcodec = fmt.get("vcodec", "none") or "none"
        if acodec != "none" and vcodec == "none":
            abr = float(fmt.get("abr") or fmt.get("tbr") or 0.0)
            if abr > best_audio_abr:
                best_audio_abr = abr
                best_audio = fmt
            if any(aac_sub in acodec.lower() for aac_sub in ("aac", "mp4a")) and abr > best_aac_abr:
                best_aac_abr = abr
                best_aac_audio = fmt

    best_audio_id = best_audio.get("format_id") if best_audio else None
    best_audio_size = (
        (best_audio.get("filesize") or best_audio.get("filesize_approx"))
        if best_audio else None
    )
    if not best_audio_size and best_audio_abr and duration:
        best_audio_size = int((best_audio_abr * 125) * duration)

    aac_audio_id = (best_aac_audio.get("format_id") if best_aac_audio else None) or best_audio_id
    aac_audio_size = (
        (best_aac_audio.get("filesize") or best_aac_audio.get("filesize_approx"))
        if best_aac_audio else best_audio_size
    )

    # If no separate audio-only stream was found, check for combined audio/video streams
    if not best_audio:
        for fmt in formats:
            acodec = fmt.get("acodec", "none") or "none"
            if acodec != "none" or fmt.get("height"):
                best_audio = fmt
                best_audio_abr = float(fmt.get("abr") or fmt.get("tbr") or 192.0)
                best_audio_id = fmt.get("format_id")
                best_audio_size = fmt.get("filesize") or fmt.get("filesize_approx")
                aac_audio_id = best_audio_id
                aac_audio_size = best_audio_size
                break

    # 2. Extract video streams grouped by height
    # Map height -> list of video formats
    by_height: Dict[int, List[Dict[str, Any]]] = {}

    for fmt in formats:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec", "none") or "none"
        ext = fmt.get("ext", "mp4")

        # Ignore true audio-only
        if vcodec == "none" and not height:
            continue

        if not height or height < 144:
            height = 720

        # Skip storyboards and low-quality manifests
        protocol = fmt.get("protocol", "") or ""
        if "mhtml" in protocol or ext in ("mhtml",):
            continue

        if height not in by_height:
            by_height[height] = []
        by_height[height].append(fmt)

    # Check per-platform quality cap from registry
    max_height_cap = 4320
    if url:
        try:
            reg = get_platform_registry()
            plat = reg.find_by_url(url)
            if plat and plat.max_quality_expected:
                cap_str = plat.max_quality_expected.lower()
                if "720" in cap_str:
                    max_height_cap = 720
                elif "1080" in cap_str:
                    max_height_cap = 1080
                elif "4k" in cap_str or "2160" in cap_str:
                    max_height_cap = 2160
        except Exception:
            pass

    format_options: List[FormatOption] = []
    sorted_heights = sorted(by_height.keys(), reverse=True)

    # Filter by height cap
    filtered_heights = [h for h in sorted_heights if h <= max_height_cap]
    if not filtered_heights and sorted_heights:
        filtered_heights = sorted_heights

    is_overall_best = True

    for height in filtered_heights:
        fmts_at_height = by_height[height]

        # A. Find highest fidelity stream (Original Best)
        def score_original(f: Dict[str, Any]) -> float:
            score = float(f.get("tbr") or f.get("vbr") or 0.0)
            fps = float(f.get("fps") or 30.0)
            score += fps * 10
            dyn = (f.get("dynamic_range") or "").upper()
            if "HDR" in dyn:
                score += 500
            # Prefer modern codecs (AV1 > VP9 > H264)
            vc = (f.get("vcodec") or "").lower()
            if "av01" in vc:
                score += 300
            elif "vp09" in vc:
                score += 150
            return score

        best_orig_fmt = max(fmts_at_height, key=score_original)

        # B. Find best H.264/AVC stream for Compatible MP4
        h264_fmts = [
            f for f in fmts_at_height
            if any(h in (f.get("vcodec") or "").lower() for h in ("avc1", "h264", "x264")) or f.get("ext") == "mp4"
        ]
        best_h264_fmt = max(h264_fmts, key=lambda f: float(f.get("tbr") or f.get("vbr") or 0.0)) if h264_fmts else best_orig_fmt

        # Build Original Best option
        v_id = best_orig_fmt.get("format_id", "")
        fps = float(best_orig_fmt.get("fps") or 30.0)
        acodec = best_orig_fmt.get("acodec", "none") or "none"
        vcodec = best_orig_fmt.get("vcodec", "")
        orig_ext = best_orig_fmt.get("ext", "mp4")
        dyn_range = (best_orig_fmt.get("dynamic_range") or "").upper()
        is_hdr = "HDR" in dyn_range

        # Quality label
        if height >= 4320:
            res_label = f"8K ({height}p)"
        elif height >= 2160:
            res_label = f"4K ({height}p)"
        elif height >= 1440:
            res_label = f"2K ({height}p)"
        elif height >= 1080:
            res_label = "1080p (Full HD)"
        elif height >= 720:
            res_label = "720p (HD)"
        elif height >= 480:
            res_label = "480p (SD)"
        else:
            res_label = f"{height}p"

        tags = []
        if fps >= 50:
            tags.append(f"{int(fps)}fps")
        if is_hdr:
            tags.append("HDR")

        tag_str = f" {' '.join(tags)}" if tags else ""

        # Size calculation
        v_size = best_orig_fmt.get("filesize") or best_orig_fmt.get("filesize_approx")
        if not v_size:
            v_tbr = float(best_orig_fmt.get("tbr") or best_orig_fmt.get("vbr") or 0.0)
            if v_tbr and duration:
                v_size = int((v_tbr * 125) * duration)

        # Check if best_audio is a dedicated audio-only stream (no video/height)
        is_true_audio_stream = bool(best_audio and (best_audio.get("vcodec") == "none" and not best_audio.get("height")))

        total_orig_size = v_size
        if acodec == "none" and best_audio_id and is_true_audio_stream:
            combined_orig_id = f"{v_id}+{best_audio_id}"
            if v_size and best_audio_size:
                total_orig_size = v_size + best_audio_size
        else:
            combined_orig_id = v_id

        # 1. Add Original Best option
        format_options.append(
            FormatOption(
                format_id=combined_orig_id,
                resolution=f"{height}p",
                height=height,
                fps=fps,
                ext=orig_ext if orig_ext in ("mp4", "webm", "mkv") else "mp4",
                format_note=f"{res_label}{tag_str} • Best Quality",
                filesize_approx=total_orig_size,
                is_audio_only=False,
                abr=best_audio_abr if acodec == "none" else best_orig_fmt.get("abr"),
                vcodec=vcodec,
                acodec=acodec if acodec != "none" else (best_audio.get("acodec") if best_audio else None),
                is_hdr=is_hdr,
                dynamic_range=dyn_range or "SDR",
                tbr=float(best_orig_fmt.get("tbr") or best_orig_fmt.get("vbr") or 0.0),
                mode="original",
                is_best=is_overall_best,
            )
        )
        is_overall_best = False

        # 2. Add Compatible MP4 option (if different from original)
        if best_h264_fmt and (best_h264_fmt.get("format_id") != best_orig_fmt.get("format_id") or orig_ext != "mp4"):
            h264_id = best_h264_fmt.get("format_id", "")
            h264_acodec = best_h264_fmt.get("acodec", "none") or "none"
            h264_size = best_h264_fmt.get("filesize") or best_h264_fmt.get("filesize_approx")
            if not h264_size:
                h_tbr = float(best_h264_fmt.get("tbr") or best_h264_fmt.get("vbr") or 0.0)
                if h_tbr and duration:
                    h264_size = int((h_tbr * 125) * duration)

            total_h264_size = h264_size
            if h264_acodec == "none" and aac_audio_id and is_true_audio_stream:
                combined_h264_id = f"{h264_id}+{aac_audio_id}"
                if h264_size and aac_audio_size:
                    total_h264_size = h264_size + aac_audio_size
            else:
                combined_h264_id = h264_id

            format_options.append(
                FormatOption(
                    format_id=combined_h264_id,
                    resolution=f"{height}p",
                    height=height,
                    fps=fps,
                    ext="mp4",
                    format_note=f"{res_label} • Compatible MP4 (H.264)",
                    filesize_approx=total_h264_size,
                    is_audio_only=False,
                    abr=best_aac_abr if h264_acodec == "none" else best_h264_fmt.get("abr"),
                    vcodec="h264",
                    acodec="aac",
                    is_hdr=False,
                    dynamic_range="SDR",
                    tbr=float(best_h264_fmt.get("tbr") or best_h264_fmt.get("vbr") or 0.0),
                    mode="compatible_mp4",
                    is_best=False,
                )
            )

    # 4. Add Audio-Only options
    if best_audio:
        # Best Original Audio (M4A or Opus)
        best_audio_ext = best_audio.get("ext", "m4a")
        if best_audio_ext in ("mp4", "webm", "mkv", "mov"):
            best_audio_ext = "m4a"
        format_options.append(
            FormatOption(
                format_id=best_audio.get("format_id", "bestaudio"),
                resolution=None,
                height=None,
                fps=None,
                ext=best_audio_ext,
                format_note=f"Audio Only ({int(best_audio_abr)} kbps {best_audio_ext.upper()})" if best_audio_abr else f"Audio Only ({best_audio_ext.upper()})",
                filesize_approx=best_audio_size,
                is_audio_only=True,
                abr=best_audio_abr,
                acodec=best_audio.get("acodec"),
                mode="original",
            )
        )

        # Universal MP3 (High Quality 320kbps)
        format_options.append(
            FormatOption(
                format_id=f"{best_audio.get('format_id', 'bestaudio')}+mp3_320",
                resolution=None,
                height=None,
                fps=None,
                ext="mp3",
                format_note="Audio Only (MP3 320 kbps High Quality)",
                filesize_approx=best_audio_size,
                is_audio_only=True,
                abr=320.0,
                acodec="mp3",
                mode="compatible_mp4",
            )
        )

        # Universal MP3 (Standard 192kbps)
        format_options.append(
            FormatOption(
                format_id=f"{best_audio.get('format_id', 'bestaudio')}+mp3",
                resolution=None,
                height=None,
                fps=None,
                ext="mp3",
                format_note="Audio Only (MP3 Standard Quality)",
                filesize_approx=best_audio_size,
                is_audio_only=True,
                abr=192.0,
                acodec="mp3",
                mode="compatible_mp4",
            )
        )

    return format_options


def extract_media_info(url: str, bypass_cache: bool = False) -> MediaInfoResponse:
    """
    Synchronously extracts media metadata using yt-dlp in Python library mode.
    Caches successful extractions for CACHE_TTL_SECONDS and errors for CACHE_ERROR_TTL_SECONDS.
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
                return MediaInfoResponse.model_validate_json(cached_json)

            cached_err = redis_client.get(err_cache_key)
            if cached_err:
                err_data = json.loads(cached_err)
                logger.info("Cache HIT (negative error cache) for media URL [%s]", canonical_url)
                raise AppError(
                    status_code=err_data.get("status_code", 400),
                    error_code=err_data.get("error_code", "UNSUPPORTED_URL_OR_PLATFORM"),
                    message=err_data.get("message", "Unable to extract media information."),
                )
        except AppError:
            raise
        except Exception as e:
            logger.debug("Redis cache read failed: %s", str(e))

    # 2. Match platform and adapter
    reg = get_platform_registry()
    matched_plat = reg.find_by_url(url)
    platform_id = matched_plat.id if matched_plat else None
    platform_tier = matched_plat.tier if matched_plat else None
    adapter = get_platform_adapter(platform_id)

    target_url = adapter.canonicalize_url(canonical_url)
    ydl_opts = get_ydl_options()
    adapter_opts = adapter.get_ydl_options(target_url)
    if adapter_opts:
        ydl_opts.update(adapter_opts)

    info_dict = None
    try:
        with safe_network_guard():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(target_url, download=False)
    except Exception as err:
        logger.info("Standard yt-dlp extraction failed for %s, trying adapter custom extraction: %s", target_url, str(err))
        custom_res = adapter.extract_custom_media(target_url)
        if custom_res:
            if custom_res.get("type") == "resolved_url":
                resolved_url = custom_res["url"]
                try:
                    with safe_network_guard():
                        with yt_dlp.YoutubeDL(get_ydl_options()) as ydl:
                            info_dict = ydl.extract_info(resolved_url, download=False)
                except Exception:
                    pass
            elif "formats" in custom_res:
                info_dict = custom_res

        if not info_dict:
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

    # Match platform from registry
    platform_id = None
    platform_tier = None
    try:
        reg = get_platform_registry()
        matched_plat = reg.find_by_url(url)
        if matched_plat:
            platform_id = matched_plat.id
            platform_tier = matched_plat.tier
    except Exception:
        pass

    # Clean formats
    raw_formats = info_dict.get("formats") or []
    clean_formats = normalize_formats(raw_formats, duration, url=url)

    result = MediaInfoResponse(
        id=str(info_dict.get("id") or "media"),
        title=clean_title,
        url=str(info_dict.get("webpage_url") or url),
        thumbnail_url=thumbnail_url,
        duration=duration,
        uploader=info_dict.get("uploader") or info_dict.get("channel"),
        is_live=bool(info_dict.get("is_live")),
        formats=clean_formats,
        platform_id=platform_id,
        platform_tier=platform_tier,
        extractor_key=info_dict.get("extractor_key"),
    )

    # Store successful extraction in Redis
    if redis_client:
        try:
            redis_client.setex(cache_key, settings.CACHE_TTL_SECONDS, result.model_dump_json())
            logger.info("Stored media info in Redis cache with TTL %ds for [%s]", settings.CACHE_TTL_SECONDS, canonical_url)
        except Exception as e:
            logger.debug("Failed to write to Redis cache: %s", str(e))

    return result
