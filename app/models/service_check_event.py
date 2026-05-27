from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class ServiceCheckEvent(Base):
    __tablename__ = "service_check_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False)

    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)

    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )