import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class JobStatus(str, enum.Enum):
    """Lifecycle stages of a video download job."""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class DownloadJob(Base, TimestampMixin):
    """
    Tracks an asynchronous media download task, its progress,
    and ephemeral file metadata.
    """
    __tablename__ = "download_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )

    # Cryptographic hash of canonical URL for rapid deduplication / lookups
    url_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format_id: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_audio_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Execution status & live metrics
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", create_type=False),
        default=JobStatus.QUEUED,
        index=True,
        nullable=False,
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    speed: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    eta: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Ephemeral storage attributes
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_ext: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # Expiry for janitor eviction
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )

    # Error tracking
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Truncated HMAC hash of client IP for concurrency and rate caps (never stores raw IP)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", JobStatus.QUEUED)
        kwargs.setdefault("progress", 0.0)
        kwargs.setdefault("is_audio_only", False)
        super().__init__(**kwargs)

    __table_args__ = (
        Index("ix_download_jobs_status_expires", "status", "expires_at"),
        Index("ix_download_jobs_ip_status", "ip_hash", "status"),
    )

