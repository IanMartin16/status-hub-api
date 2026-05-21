from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.service_status import ServiceStatusRecord


def utc_now():
    return datetime.now(timezone.utc)


FAILURE_STATUSES = {
    "degraded",
    "down",
    "platform_issue",
    "unknown",
}


class StatusRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_services(self) -> list[Service]:
        return (
            self.db.query(Service)
            .filter(Service.is_active.is_(True))
            .order_by(Service.name.asc())
            .all()
        )

    def get_latest_status_map(self) -> dict[int, ServiceStatusRecord]:
        rows = self.db.query(ServiceStatusRecord).all()
        return {row.service_id: row for row in rows}

    def get_status_by_service_id(
        self,
        service_id: int,
    ) -> ServiceStatusRecord | None:
        return (
            self.db.query(ServiceStatusRecord)
            .filter(ServiceStatusRecord.service_id == service_id)
            .first()
        )

    def upsert_status(
        self,
        service_id: int,
        status: str,
        latency_ms: int | None,
        http_status: int | None,
        message: str | None,
        raw_error: str | None,
    ) -> ServiceStatusRecord:
        now = utc_now()

        existing = self.get_status_by_service_id(service_id)

        if existing:
            status_changed = existing.status != status

            existing.status = status
            existing.latency_ms = latency_ms
            existing.http_status = http_status
            existing.message = message
            existing.raw_error = raw_error
            existing.last_checked_at = now

            if status_changed:
                existing.last_status_change_at = now

            if status in FAILURE_STATUSES:
                existing.consecutive_failures = (
                    existing.consecutive_failures or 0
                ) + 1
            else:
                existing.consecutive_failures = 0

            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        created = ServiceStatusRecord(
            service_id=service_id,
            status=status,
            latency_ms=latency_ms,
            http_status=http_status,
            message=message,
            raw_error=raw_error,
            consecutive_failures=1 if status in FAILURE_STATUSES else 0,
            last_status_change_at=now,
            last_checked_at=now,
        )

        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created