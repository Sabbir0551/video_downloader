import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.endpoints.health import router as root_health_router
from app.api.v1.router import api_v1_router
from app.api.web import router as web_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import request_id_ctx, setup_structured_logging
from app.db.session import init_db
from app.middlewares.security_headers import SecurityHeadersMiddleware

# Configure structured JSON logging
setup_structured_logging(debug=settings.DEBUG)
logger = logging.getLogger("anystream.main")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Assigns unique request UUID and attaches it to logging context and response headers."""
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    logger.info("Initializing %s v%s in [%s] mode...", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)
    try:
        init_db()
    except Exception as e:
        logger.error("Database initialization failed: %s", str(e))
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(f"Database initialization failure in production: {str(e)}") from e
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """FastAPI application factory with security hardening."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # 1. Tracing & Security Middlewares
    app.add_middleware(RequestTracingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. Strict CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$" if settings.ENVIRONMENT != "production" else None,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,
    )

    # 3. Global Domain Exception Handler (Structured Error Contract)
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    # 4. Pydantic Request Validation Error Handler
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        sanitized_errors = []
        for err in exc.errors():
            sanitized_errors.append({
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "type": err.get("type"),
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "REQUEST_VALIDATION_ERROR",
                "message": "The submitted payload is invalid or contains prohibited characters.",
                "details": {"validation_errors": sanitized_errors},
            },
        )

    # 5. Global Unhandled Exception Handler (Never exposes raw stack traces)
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled server exception: %s", str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing your request. Please try again later.",
                "details": {},
            },
        )

    # 6. Mount Web UI, Health, and API v1 Router
    app.include_router(web_router, prefix="")
    app.include_router(root_health_router, prefix="", tags=["System"])
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()

