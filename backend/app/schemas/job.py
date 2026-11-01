import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.job import JobStatus


class CreateJobRequest(BaseModel):
    """Payload for submitting a background download job."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format_id": "best",
                "audio_only": False,
                "quality_label": "Best Video",
                "mode": "original",
            }
        }
    }

    url: str = Field(..., description="Target video URL", max_length=2048)
    format_id: str = Field(default="best", description="Target format selector", max_length=128)
    audio_only: bool = Field(default=False, description="Convert/download as audio file")
    quality_label: Optional[str] = Field(default=None, description="Display label (e.g. 720p)", max_length=64)
    captcha_token: Optional[str] = Field(default=None, description="Turnstile CAPTCHA token if required")
    mode: str = Field(default="original", description="Mode: 'original' or 'compatible_mp4'")

    @model_validator(mode="before")
    @classmethod
    def preprocess_input(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"url": data.strip(), "format_id": "best"}
        if isinstance(data, dict):
            res = dict(data)
            # If standard "url" field is not provided or empty, check keys
            if "url" not in res or not res["url"]:
                for k in list(data.keys()):
                    if isinstance(k, str) and k.strip().startswith(("http://", "https://")):
                        res["url"] = k.strip()
                        break
            # Default format_id if missing or empty
            if not res.get("format_id"):
                res["format_id"] = "best"
            return res
        return data

    @field_validator("format_id")
    @classmethod
    def sanitize_format_id(cls, v: str) -> str:
        v = v.strip()
        # Strictly allow alphanumeric characters, hyphens, underscores, slashes, brackets, and plus signs
        if not re.match(r"^[a-zA-Z0-9_\-\+\/\[\]\<\=\>\:]{1,128}$", v):
            raise ValueError("format_id contains invalid characters.")
        return v


class JobStatusResponse(BaseModel):
    """Real-time lifecycle and progress representation of a download job."""

    job_id: UUID = Field(..., description="Unique job UUID")
    status: JobStatus = Field(..., description="Current job status")
    progress: Optional[float] = Field(default=None, description="Progress percentage (0.0 to 100.0)")
    speed: Optional[str] = Field(default=None, description="Current download throughput string")
    eta: Optional[int] = Field(default=None, description="Estimated time of completion in seconds")
    file_size: Optional[int] = Field(default=None, description="Total byte size of finalized artifact")
    download_url: Optional[str] = Field(default=None, description="Signed temporary download link")
    created_at: Optional[datetime] = Field(default=None, description="Job enqueue timestamp in UTC")
    expires_at: Optional[datetime] = Field(default=None, description="Pruning expiration timestamp in UTC")
    error_code: Optional[str] = Field(default=None, description="Canonical error code on failure")
    error_message: Optional[str] = Field(default=None, description="Sanitized human-readable error description")
    job_access_token: Optional[str] = Field(default=None, description="Signed authorization secret for polling and cancellations")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "PROCESSING",
                "progress": 45.5,
                "speed": "2.4 MB/s",
                "eta": 15,
                "file_size": 25000000,
                "download_url": "/api/v1/downloads/550e8400-e29b-41d4-a716-446655440000/file?token=mock_tok",
                "created_at": "2026-10-30T02:00:00Z",
                "expires_at": "2026-10-30T02:30:00Z",
                "error_code": None,
                "error_message": None,
                "job_access_token": "jat_0123456789abcdef",
            }
        },
    }


class ProgressEvent(BaseModel):
    """Real-time SSE event payload published over Redis PubSub."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    progress: float = Field(default=0.0, description="Percentage progress")
    speed: Optional[str] = Field(default=None, description="Download rate string")
    eta: Optional[int] = Field(default=None, description="Seconds remaining")
    file_size: Optional[int] = Field(default=None, description="Artifact byte size")
    download_url: Optional[str] = Field(default=None, description="Expiring download link")
