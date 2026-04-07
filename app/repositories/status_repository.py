from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.service import Service
from app.models.service_status import ServiceStatusRecord


def utc_now():
    return datetime.now(timezone.utc)


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

    def upsert_status(
        self,
        service_id: int,
        status: str,
        latency_ms: int | None,
        http_status: int | None,
        message: str | None,
        raw_error: str | None,
    ) -> ServiceStatusRecord:
        existing = (
            self.db.query(ServiceStatusRecord)
            .filter(ServiceStatusRecord.service_id == service_id)
            .first()
        )

        if existing:
            existing.status = status
            existing.latency_ms = latency_ms
            existing.http_status = http_status
            existing.message = message
            existing.raw_error = raw_error
            existing.last_checked_at = utc_now()
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
            last_checked_at=utc_now(),
        )
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created