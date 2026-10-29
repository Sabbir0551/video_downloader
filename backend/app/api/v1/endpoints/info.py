import asyncio
from fastapi import APIRouter, Request, status

from app.core.config import settings
from app.core.rate_limit import check_rate_limit, get_client_ip_hash
from app.core.ssrf import validate_url_security
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
async def get_media_info(request: Request, payload: UrlExtractRequest) -> MediaInfoResponse:
    """
    Validates URL security against SSRF and extracts video details.
    """
    # 1. Hashed client IP (never stores raw IP) & Rate Limit Check (15 req/min)
    ip_hash = get_client_ip_hash(request)
    check_rate_limit(ip_hash, "info", settings.RATE_LIMIT_EXTRACT_PER_MINUTE)

    # 2. SSRF Pre-Resolution & Scheme Guard
    clean_url, _ = validate_url_security(payload.url)

    # 3. Asynchronous execution of yt-dlp library call (run in worker thread to prevent event loop blocking)
    info_response = await asyncio.to_thread(extract_media_info, clean_url)

    return info_response


# Mount alias endpoints to maintain backwards-compatibility
@router.post(
    "/extract",
    response_model=MediaInfoResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def extract_media_alias(request: Request, payload: UrlExtractRequest) -> MediaInfoResponse:
    return await get_media_info(request, payload)


@router.post(
    "/extract/info",
    response_model=MediaInfoResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def extract_media_info_alias(request: Request, payload: UrlExtractRequest) -> MediaInfoResponse:
    return await get_media_info(request, payload)

