from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AbuseLog(Base):
    """
    Structured audit trail for security incidents and abuse anomalies.
    IP addresses are stored exclusively as non-reversible salted HMACs.
    """
    __tablename__ = "abuse_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_abuse_logs_ip_event_time", "ip_hash", "event_type", "timestamp"),
    )

