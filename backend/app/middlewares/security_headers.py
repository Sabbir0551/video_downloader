from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends security headers to all HTTP responses to protect against
    Clickjacking, MIME-sniffing, XSS, and unauthorized framing.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Anti-MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Frame protection (Anti-Clickjacking)
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS auditor
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer privacy policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Device hardware access policy
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # Content Security Policy
        path = request.url.path
        if path.startswith(("/docs", "/redoc", "/openapi.json")):
            # Permit Swagger UI / ReDoc CDN assets & inline initialization scripts
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "frame-ancestors 'none';"
            )
        else:
            # Strict API baseline
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        # HSTS (Strict-Transport-Security) for production environments
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

        return response

