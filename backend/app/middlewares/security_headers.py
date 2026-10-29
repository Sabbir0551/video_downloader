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
        if path == "/" or path.startswith(("/docs", "/redoc", "/openapi.json")):
            # Permit Web UI & Swagger UI assets, inline scripts/styles, API fetch, and video thumbnails
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 http://localhost:* http://127.0.0.1:* ws: https:; "
                "frame-ancestors 'none';"
            )
        else:
            # API baseline
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        # HSTS (Strict-Transport-Security) for production environments
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

        return response

