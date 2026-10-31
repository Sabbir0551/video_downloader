import asyncio
import hashlib
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, ContentBlockedLegalError
from app.core.rate_limit import check_rate_limit, get_client_ip_hash, get_raw_client_ip
from app.core.security import normalize_video_url, verify_turnstile_captcha
from app.core.ssrf import safe_network_guard, validate_url_security
from app.db.session import get_db
from app.models.takedown import TakedownRecord, TakedownStatus
from app.schemas.common import ErrorResponse
from app.schemas.extract import MediaInfoResponse, UrlExtractRequest
from app.services.extractor import extract_media_info

router = APIRouter()


@router.post(
    "/info",
    response_model=MediaInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect media URL and list formats",
    description="Validates target URL against SSRF policy, resolves media details via yt-dlp, and returns clean quality options.",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid URL, private network destination, or unsupported host",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "SSRF_DESTINATION_FORBIDDEN",
                        "message": "Access to host '127.0.0.1' is denied by security policy.",
                        "details": {"hostname": "127.0.0.1"},
                    }
                }
            },
        },
        403: {
            "model": ErrorResponse,
            "description": "DRM-protected or paywalled content",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "MEDIA_DRM_PROTECTED",
                        "message": "This media stream is DRM-protected and cannot be downloaded.",
                        "details": {},
                    }
                }
            },
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded for client IP or upstream provider",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests to /info. Rate limit is 15 per minute.",
                        "details": {"limit": 15, "window_seconds": 60},
                    }
                }
            },
        },
        451: {
            "model": ErrorResponse,
            "description": "Content unavailable due to legal or DMCA takedown",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "LEGAL_TAKEDOWN_BLOCK",
                        "message": "This content has been blocked due to a copyright or legal notice.",
                        "details": {},
                    }
                }
            },
        },
    },
)
async def get_media_info(
    request: Request,
    payload: UrlExtractRequest,
    db: AsyncSession = Depends(get_db),
) -> MediaInfoResponse:
    """
    Validates URL security against SSRF, enforces takedown blocks, and extracts video details.
    """
    # 1. Hashed client IP (never stores raw IP) & Rate Limit Check (15 req/min)
    ip_hash = get_client_ip_hash(request)
    check_rate_limit(ip_hash, "info", settings.RATE_LIMIT_EXTRACT_PER_MINUTE)

    # 2. CAPTCHA verification if required
    raw_ip = get_raw_client_ip(request)
    if settings.CLOUDFLARE_TURNSTILE_SECRET_KEY or payload.captcha_token:
        captcha_valid = await verify_turnstile_captcha(payload.captcha_token, raw_ip)
        if not captcha_valid:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="CAPTCHA_VERIFICATION_FAILED",
                message="Cloudflare Turnstile CAPTCHA verification failed. Please try again.",
            )

    # 3. SSRF Pre-Resolution & Scheme Guard
    clean_url, _ = validate_url_security(payload.url)

    # 4. Check for active legal takedown / blacklist blocks
    canonical_url, canonical_id = normalize_video_url(clean_url)
    raw_url_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
    canon_url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

    conds = [
        TakedownRecord.url_hash.in_([raw_url_hash, canon_url_hash]),
    ]
    if canonical_id:
        conds.append(TakedownRecord.channel_id == canonical_id)

    takedown_stmt = select(TakedownRecord).where(
        or_(*conds),
        TakedownRecord.status != TakedownStatus.REJECTED,
    )
    takedown_res = await db.execute(takedown_stmt)
    if takedown_res.scalars().first():
        raise ContentBlockedLegalError("This content has been blocked due to a copyright or legal notice.")

    # 5. Guarded asynchronous execution of yt-dlp library call with network sandbox
    def _guarded_extract():
        with safe_network_guard():
            return extract_media_info(clean_url)

    info_response = await asyncio.to_thread(_guarded_extract)

    return info_response


# Mount alias endpoints to maintain backwards-compatibility
@router.post(
    "/extract",
    response_model=MediaInfoResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def extract_media_alias(
    request: Request,
    payload: UrlExtractRequest,
    db: AsyncSession = Depends(get_db),
) -> MediaInfoResponse:
    return await get_media_info(request, payload, db)


@router.post(
    "/extract/info",
    response_model=MediaInfoResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def extract_media_info_alias(
    request: Request,
    payload: UrlExtractRequest,
    db: AsyncSession = Depends(get_db),
) -> MediaInfoResponse:
    return await get_media_info(request, payload, db)

