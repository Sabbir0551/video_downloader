from typing import Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Platform health diagnostics schema."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str = Field(..., description="API software version")
    ytdlp_version: str = Field(..., description="Active yt-dlp library version")
    database: bool = Field(..., description="PostgreSQL connectivity state")
    redis: bool = Field(..., description="Redis connectivity state")

