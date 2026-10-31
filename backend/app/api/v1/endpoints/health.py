import shutil
from typing import Optional

import redis
import yt_dlp
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse
from app.worker.celery_app import celery_app

router = APIRouter()


async def check_database(db: AsyncSession) -> bool:
    """Attempts a lightweight ping against the database."""
    try:
        res = await db.execute(text("SELECT 1"))
        return res.scalar() == 1
    except Exception:
        return False


def check_redis() -> bool:
    """Pings Redis if configured."""
    try:
        r = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        return bool(r.ping())
    except Exception:
        return False


def count_celery_workers() -> int:
    """Queries running Celery workers with a short timeout."""
    try:
        pings = celery_app.control.ping(timeout=0.3)
        return len(pings) if pings else 0
    except Exception:
        return 0


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Platform health and diagnostics",
    description="Returns service status, version, and dependency connectivity (Postgres, Redis, FFmpeg, Node, Disk, Workers).",
)
async def health_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Full platform diagnostic verification."""
    ytdlp_ver = getattr(yt_dlp.version, "__version__", "unknown")
    db_ok = await check_database(db)
    redis_ok = check_redis()
    ffmpeg_ok = bool(shutil.which("ffmpeg"))
    node_ok = bool(shutil.which("node"))

    disk_mb: Optional[int] = None
    try:
        disk_mb = int(shutil.disk_usage(settings.STORAGE_DIR).free // (1024 * 1024))
    except Exception:
        pass

    worker_count = count_celery_workers()

    # Determine status level
    if db_ok and redis_ok:
        health_status = "healthy"
    elif db_ok or redis_ok:
        health_status = "degraded"
    else:
        health_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=health_status,
        version=settings.VERSION,
        ytdlp_version=ytdlp_ver,
        database=db_ok,
        redis=redis_ok,
        ffmpeg=ffmpeg_ok,
        node=node_ok,
        disk_free_mb=disk_mb,
        celery_workers=worker_count,
    )


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Returns 200 OK as long as the HTTP process is responsive.",
)
async def liveness_check() -> LivenessResponse:
    return LivenessResponse(status="alive")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Verifies essential database, redis, and disk requirements before receiving traffic.",
)
async def readiness_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> ReadinessResponse:
    db_ok = await check_database(db)
    redis_ok = check_redis()

    disk_ok = True
    try:
        free_bytes = shutil.disk_usage(settings.STORAGE_DIR).free
        if free_bytes < settings.MIN_FREE_DISK_BYTES:
            disk_ok = False
    except Exception:
        pass

    is_ready = db_ok and redis_ok and disk_ok
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        database=db_ok,
        redis=redis_ok,
        disk_ok=disk_ok,
    )
