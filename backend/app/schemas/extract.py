from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class UrlExtractRequest(BaseModel):
    """Payload for submitting a URL for metadata inspection."""

    url: str = Field(..., description="Target public video URL", max_length=2048)
    captcha_token: Optional[str] = Field(
        default=None,
        description="Optional Cloudflare Turnstile token for high-frequency clients",
        max_length=1024,
    )

    @model_validator(mode="before")
    @classmethod
    def preprocess_input(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"url": data.strip()}
        if isinstance(data, dict):
            # If standard "url" field is provided
            if "url" in data and data["url"]:
                return data
            # Check if user accidentally pasted the URL as the JSON key or body
            for k, v in data.items():
                if isinstance(k, str) and k.strip().startswith(("http://", "https://")):
                    return {"url": k.strip(), "captcha_token": data.get("captcha_token")}
        return data

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class FormatOption(BaseModel):
    """Describes a single downloadable stream or quality preset."""

    format_id: str = Field(..., description="Internal format selector for yt-dlp", max_length=64)
    resolution: Optional[str] = Field(default=None, description="Display resolution (e.g. 1080p, 720p)")
    height: Optional[int] = Field(default=None, description="Vertical pixel count")
    fps: Optional[float] = Field(default=None, description="Frames per second")
    ext: str = Field(..., description="File container extension (mp4, webm, m4a, mp3)", max_length=16)
    format_note: str = Field(..., description="Human-readable quality description", max_length=128)
    filesize_approx: Optional[int] = Field(default=None, description="Estimated byte count")
    is_audio_only: bool = Field(default=False, description="Flag identifying audio-only tracks")
    abr: Optional[float] = Field(default=None, description="Audio bitrate in kbps")


class MediaInfoResponse(BaseModel):
    """Complete sanitized metadata payload returned upon URL extraction."""

    id: str = Field(..., description="Upstream platform video ID")
    title: str = Field(..., description="Sanitized video title")
    url: str = Field(..., description="Canonical media URL")
    thumbnail_url: str = Field(..., description="Public image thumbnail URL")
    duration: int = Field(..., description="Media duration in seconds", ge=0)
    uploader: Optional[str] = Field(default=None, description="Channel or creator name")
    is_live: bool = Field(default=False, description="Whether media is an active livestream")
    formats: List[FormatOption] = Field(default_factory=list, description="Available quality streams")

