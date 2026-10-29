import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TakedownStatus(str, enum.Enum):
    """Status stages for a DMCA or legal takedown submission."""
    RECEIVED = "RECEIVED"
    BLOCKED_PENDING_REVIEW = "BLOCKED_PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TakedownRecord(Base, TimestampMixin):
    """
    Stores copyrighted or blocked URLs/channels to prevent downloads.
    """
    __tablename__ = "takedown_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )

    url_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    channel_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)

    copyrighted_work_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    requester_name: Mapped[str] = mapped_column(String(256), nullable=False)
    requester_email: Mapped[str] = mapped_column(String(256), nullable=False)
    statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[TakedownStatus] = mapped_column(
        Enum(TakedownStatus, name="takedown_status_enum", create_type=False),
        default=TakedownStatus.BLOCKED_PENDING_REVIEW,
        index=True,
        nullable=False,
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", TakedownStatus.BLOCKED_PENDING_REVIEW)
        super().__init__(**kwargs)

    __table_args__ = (
        Index("ix_takedown_url_hash_status", "url_hash", "status"),
    )

