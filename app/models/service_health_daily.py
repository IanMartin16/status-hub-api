from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class ServiceHealthDaily(Base):
    __tablename__ = "service_health_daily"

    __table_args__ = (
        UniqueConstraint(
            "service_id",
            "day",
            name="uq_service_health_daily_service_day",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id"),
        nullable=False,
        index=True,
    )

    day: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    total_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    operational_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    degraded_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    down_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    platform_issue_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    unknown_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    availability_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    avg_latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    max_latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )