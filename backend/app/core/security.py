import hashlib
import hmac
import json
import re
import time
import unicodedata
import urllib.parse
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings
from app.core.errors import DownloadTokenInvalidError

# Reserved Windows / POSIX file names
RESERVED_FILENAMES = {
    "con", "prn", "aux", "nul",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
}


def hash_ip(ip_address: str, salt: str = "") -> str:
    """
    Creates a non-reversible cryptographic hash of a client IP address.
    Protects user privacy while allowing rate limiting and abuse mitigation.
    Uses daily rotating salt for forward privacy when no explicit salt is supplied.
    """
    if salt:
        active_salt = salt
    else:
        # Rotating daily salt
        daily_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        active_salt = f"{settings.IP_HASH_SALT}:{daily_stamp}"

    mac = hmac.new(
        key=active_salt.encode("utf-8"),
        msg=ip_address.strip().encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return mac.hexdigest()[:32]


def generate_job_access_token(job_id: str) -> str:
    """Generates a secure HMAC-SHA256 ownership token bound to a specific job UUID."""
    sig = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=f"job:{job_id}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()[:32]
    return f"jat_{sig}"


def verify_job_access_token(token: str, job_id: str) -> bool:
    """Verifies that a job access token matches the expected signature for this job."""
    if not token:
        return False
    expected = generate_job_access_token(job_id)
    return hmac.compare_digest(token.strip(), expected)


def normalize_video_url(url: str) -> Tuple[str, str]:
    """
    Normalizes a video URL to prevent takedown or cache bypasses via trivial parameter variants.
    Returns:
        (canonical_url, canonical_id)
    """
    try:
        parsed = urllib.parse.urlparse(url.strip())
        netloc = parsed.netloc.lower()
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # YouTube variants
        if "youtube.com" in netloc or "youtu.be" in netloc:
            video_id = ""
            if "youtu.be" in netloc:
                video_id = path.lstrip("/").split("/")[0]
            elif "v" in query and query["v"]:
                video_id = query["v"][0]
            elif "/embed/" in path:
                video_id = path.split("/embed/")[1].split("/")[0]
            elif "/shorts/" in path:
                video_id = path.split("/shorts/")[1].split("/")[0]
            if video_id:
                canonical = f"https://www.youtube.com/watch?v={video_id}"
                return canonical, f"youtube:{video_id}"

        # Generic: strip common tracking params
        tracking_params = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref", "si", "feature"}
        clean_query = {k: v for k, v in query.items() if k.lower() not in tracking_params}
        new_query_str = urllib.parse.urlencode(clean_query, doseq=True)
        canonical = urllib.parse.urlunparse((parsed.scheme.lower(), netloc, path.rstrip("/"), "", new_query_str, ""))
        return canonical, ""
    except Exception:
        return url.strip(), ""


async def verify_turnstile_captcha(token: Optional[str], remote_ip: str) -> bool:
    """Verifies Cloudflare Turnstile token via Cloudflare siteverify endpoint."""
    if not settings.CLOUDFLARE_TURNSTILE_SECRET_KEY:
        return True  # Verification not enabled
    if not token:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                settings.CLOUDFLARE_TURNSTILE_VERIFY_URL,
                data={
                    "secret": settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
                    "response": token,
                    "remoteip": remote_ip,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return bool(data.get("success"))
    except Exception:
        if settings.ENVIRONMENT == "production":
            return False
    return False


def sanitize_display_title(title: str, max_length: int = 250) -> str:
    """
    Sanitizes human-readable display titles:
    - Normalizes unicode (NFKC).
    - Strips non-printable and control characters.
    - Preserves normal spaces and international scripts (Bangla, English, etc.).
    - Constrains maximum length.
    """
    if not title:
        return "Untitled Media"
    title = unicodedata.normalize("NFKC", title)
    title = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        return "Untitled Media"
    if len(title) > max_length:
        title = title[:max_length].strip()
    return title


def sanitize_filename(title: str, ext: str, max_length: int = 120) -> str:
    """
    Sanitizes user/video titles for safe HTTP Content-Disposition headers.
    - Strips path traversal characters (/, \\, .., null bytes).
    - Removes non-printable or control characters.
    - Normalizes unicode characters (NFKD).
    - Guarantees valid safe extension.
    - Prevents OS reserved filenames.
    """
    if not title:
        title = "media_download"

    # Normalize unicode
    title = unicodedata.normalize("NFKC", title)

    # Strip dangerous characters
    title = re.sub(r'[\x00-\x1f\x7f-\x9f/\\:*?"<>|]', "_", title)

    # Replace runs of whitespace and underscores
    title = re.sub(r"[\s_]+", "_", title).strip(" ._")

    # If stripped empty, fallback
    if not title:
        title = "media_download"

    # Check reserved names
    lower_name = title.lower()
    if lower_name in RESERVED_FILENAMES:
        title = f"{title}_file"

    # Truncate length
    if len(title) > max_length:
        title = title[:max_length].rstrip(" ._")

    # Clean extension
    safe_ext = re.sub(r"[^a-zA-Z0-9]", "", ext.lstrip(".")).lower()
    if not safe_ext:
        safe_ext = "mp4"

    return f"{title}.{safe_ext}"


def generate_download_token(job_id: str, file_name: str, expiry_seconds: int = 1800) -> str:
    """
    Generates a cryptographically signed, expiring download token containing the job_id.
    Structure: Base64Url(Payload) + "." + Base64Url(HMAC)
    """
    now = int(time.time())
    payload = {
        "job_id": job_id,
        "file_name": file_name[:80] if file_name else "media",
        "iat": now,
        "exp": now + expiry_seconds,
    }

    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

    signature = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=payload_b64.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    sig_b64 = urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def verify_download_token(token: str) -> Dict[str, Any]:
    """
    Validates the integrity, signature, and expiration of a download token.
    Returns the decoded payload dict.
    Raises DownloadTokenInvalidError if invalid or expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 2:
            raise DownloadTokenInvalidError("Malformed token structure.")

        payload_b64, sig_b64 = parts[0], parts[1]

        # Recompute HMAC signature
        expected_sig = hmac.new(
            key=settings.SECRET_KEY.encode("utf-8"),
            msg=payload_b64.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        # Constant time comparison to prevent timing attacks
        # Add padding back if necessary
        padded_sig = sig_b64 + "=" * (-len(sig_b64) % 4)
        provided_sig = urlsafe_b64decode(padded_sig.encode("utf-8"))

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise DownloadTokenInvalidError("Signature verification failed.")

        # Decode payload
        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_bytes = urlsafe_b64decode(padded_payload.encode("utf-8"))
        payload: Dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))

        # Expiry check
        now = int(time.time())
        if payload.get("exp", 0) < now:
            raise DownloadTokenInvalidError("Download token has expired.")

        return payload

    except DownloadTokenInvalidError:
        raise
    except Exception as err:
        raise DownloadTokenInvalidError(
            message="Token decoding or validation failed.",
            details={"error": str(err)},
        )

