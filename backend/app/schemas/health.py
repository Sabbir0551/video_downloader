from typing import Literal, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Platform health diagnostics schema."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str = Field(..., description="API software version")
    ytdlp_version: str = Field(..., description="Active yt-dlp library version")
    database: bool = Field(..., description="PostgreSQL connectivity state")
    redis: bool = Field(..., description="Redis connectivity state")
    ffmpeg: Optional[bool] = Field(default=None, description="FFmpeg binary availability")
    node: Optional[bool] = Field(default=None, description="Node.js binary availability for yt-dlp JS runtime")
    disk_free_mb: Optional[int] = Field(default=None, description="Free disk space in megabytes")
    celery_workers: Optional[int] = Field(default=None, description="Reachable Celery worker instances count")


class LivenessResponse(BaseModel):
    """Kubernetes liveness probe response schema."""
    status: Literal["alive"] = "alive"


class ReadinessResponse(BaseModel):
    """Kubernetes readiness probe response schema."""
    status: Literal["ready", "not_ready"]
    database: bool
    redis: bool
    disk_ok: bool
