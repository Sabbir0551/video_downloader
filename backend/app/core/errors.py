from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application exception with machine-readable error codes."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code,
                "message": message,
                "details": details or {},
            },
        )
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class SSRFValidationError(AppError):
    def __init__(self, message: str = "The destination host is restricted or invalid.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="SSRF_DESTINATION_FORBIDDEN",
            message=message,
            details=details,
        )


class UnsupportedUrlError(AppError):
    def __init__(self, message: str = "This URL or platform is not supported.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="UNSUPPORTED_URL_OR_PLATFORM",
            message=message,
            details=details,
        )


class DRMProtectedError(AppError):
    def __init__(self, message: str = "This media stream is DRM-protected and cannot be downloaded.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="MEDIA_DRM_PROTECTED",
            message=message,
            details=details,
        )


class MediaTooLargeError(AppError):
    def __init__(self, message: str = "The media exceeds maximum allowed duration or file size.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="MEDIA_LIMIT_EXCEEDED",
            message=message,
            details=details,
        )


class ContentBlockedLegalError(AppError):
    def __init__(self, message: str = "This content has been blocked due to a copyright or legal notice.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
            error_code="LEGAL_TAKEDOWN_BLOCK",
            message=message,
            details=details,
        )


class JobNotFoundError(AppError):
    def __init__(self, message: str = "Download job not found or has expired.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="JOB_NOT_FOUND",
            message=message,
            details=details,
        )


class DownloadTokenInvalidError(AppError):
    def __init__(self, message: str = "Download link has expired or signature is invalid.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="DOWNLOAD_TOKEN_INVALID",
            message=message,
            details=details,
        )


class RateLimitExceededError(AppError):
    def __init__(self, message: str = "Rate limit exceeded. Please wait before submitting more requests.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            details=details,
        )

