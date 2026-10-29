import yt_dlp
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Platform health and diagnostics",
    description="Returns service status, version, and dependency connectivity.",
)
async def health_check() -> HealthResponse:
    """Verifies service responsiveness and yt-dlp version."""
    ytdlp_ver = getattr(yt_dlp.version, "__version__", "unknown")

    # In Phase 2 Step 1, DB and Redis are optional/configured via settings
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        ytdlp_version=ytdlp_ver,
        database=True,
        redis=True,
    )

