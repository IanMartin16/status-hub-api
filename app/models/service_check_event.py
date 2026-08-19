from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class ServiceCheckEvent(Base):
    __tablename__ = "service_check_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    readiness: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    uptime_seconds: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    contract_version: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    checks: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    raw_error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


Index(
    "idx_service_check_events_service_checked_at",
    ServiceCheckEvent.service_id,
    ServiceCheckEvent.checked_at.desc(),
)