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
            }
        }
    }

    url: str = Field(..., description="Target video URL", max_length=2048)
    format_id: str = Field(default="best", description="Target format selector", max_length=64)
    audio_only: bool = Field(default=False, description="Convert/download as audio file")
    quality_label: Optional[str] = Field(default=None, description="Display label (e.g. 720p)", max_length=64)
    captcha_token: Optional[str] = Field(default=None, description="Turnstile CAPTCHA token if required")

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
        # Strictly allow alphanumeric characters, hyphens, underscores, slashes, and plus signs
        if not re.match(r"^[a-zA-Z0-9_\-\+\/]{1,64}$", v):
            raise ValueError("format_id contains invalid characters.")
        return v


class JobStatusResponse(BaseModel):
    """Real-time lifecycle and progress representation of a download job."""

    job_id: UUID = Field(..., description="Unique job UUID")
    status: JobStatus = Field(..., description="Current job status")
    progress: Optional[float] = Field(default=None, description="Progress percentage (0.0 to 100.0)")
    speed: Optional[str] = Field(default=None, description="Human-readable transfer speed")
    eta: Optional[int] = Field(default=None, description="Seconds remaining")
    file_size: Optional[int] = Field(default=None, description="Finalized size in bytes")
    download_url: Optional[str] = Field(default=None, description="Signed download URL when completed")
    created_at: datetime = Field(..., description="Job submission timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="File expiration timestamp")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error identifier on failure")
    error_message: Optional[str] = Field(default=None, description="User-friendly error explanation")

    @field_validator("eta", mode="before")
    @classmethod
    def parse_eta(cls, v):
        if v is not None:
            try:
                return int(round(float(v)))
            except (ValueError, TypeError):
                return None
        return None


class ProgressEvent(BaseModel):
    """Lightweight event emitted via Server-Sent Events (SSE)."""

    job_id: UUID
    status: JobStatus
    progress: float
    speed: Optional[str] = None
    eta: Optional[int] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None

