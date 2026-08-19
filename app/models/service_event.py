from datetime import datetime, timezone

from sqlalchemy import (
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


class ServiceEvent(Base):
    __tablename__ = "service_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    current_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    source_check_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "service_check_events.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


Index(
    "idx_service_events_service_occurred_at",
    ServiceEvent.service_id,
    ServiceEvent.occurred_at.desc(),
)