from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.service_status import ServiceStatusRecord
from app.models.service_check_event import ServiceCheckEvent
from app.models.service_event import ServiceEvent
from app.models.service_health_daily import ServiceHealthDaily

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
        readiness: str | None = None,
        uptime_seconds: int | None = None,
        contract_version: str | None = None,
        checks: list | None = None,
    ) -> ServiceStatusRecord:
        now = utc_now()

        existing = self.get_status_by_service_id(service_id)

        if existing:
            status_changed = existing.status != status

            existing.status = status
            existing.readiness = readiness
            existing.uptime_seconds = uptime_seconds
            existing.contract_version = contract_version
            existing.checks = checks

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
            return existing

        created = ServiceStatusRecord(
            service_id=service_id,
            status=status,

            readiness=readiness,
            uptime_seconds=uptime_seconds,
            contract_version=contract_version,
            checks=checks,

            latency_ms=latency_ms,
            http_status=http_status,
            message=message,
            raw_error=raw_error,

            consecutive_failures=(
                1 if status in FAILURE_STATUSES else 0
            ),

            last_status_change_at=now,
            last_checked_at=now,
        )

        self.db.add(created)
        return created

    def insert_check_event(
        self,
        service_id: int,
        status: str,
        latency_ms: int | None,
        http_status: int | None,
        message: str | None,
        raw_error: str | None,
        readiness: str | None = None,
        uptime_seconds: int | None = None,
        contract_version: str | None = None,
        checks: list | None = None,
    ) -> ServiceCheckEvent:
        event = ServiceCheckEvent(
            service_id=service_id,
            status=status,

            readiness=readiness,
            uptime_seconds=uptime_seconds,
            contract_version=contract_version,
            checks=checks,

            latency_ms=latency_ms,
            http_status=http_status,
            message=message,
            raw_error=raw_error,
            checked_at=utc_now(),
        )

        self.db.add(event)
        return event

    def get_recent_events_by_service(
        self,
        service_id: int,
        limit: int = 30,
    ) -> list[ServiceCheckEvent]:
        return (
            self.db.query(ServiceCheckEvent)
            .filter(ServiceCheckEvent.service_id == service_id)
            .order_by(ServiceCheckEvent.checked_at.desc())
            .limit(limit)
            .all()
        )

    def get_recent_events_map(
        self,
        service_ids: list[int],
        limit_per_service: int = 30,
    ) -> dict[int, list[ServiceCheckEvent]]:
        result: dict[int, list[ServiceCheckEvent]] = {}

        for service_id in service_ids:
            result[service_id] = self.get_recent_events_by_service(
                service_id=service_id,
                limit=limit_per_service,
            )

        return result

    def insert_service_event(
        self,
        service_id: int,
        event_type: str,
        severity: str,
        previous_status: str | None,
        current_status: str | None,
        message: str | None,
        event_metadata: dict | None,
        source_check_id: int | None,
    ) -> ServiceEvent:

        event = ServiceEvent(
            service_id=service_id,
            event_type=event_type,
            severity=severity,
            previous_status=previous_status,
            current_status=current_status,
            message=message,
            event_metadata=event_metadata,
            source_check_id=source_check_id,
        )

        self.db.add(event)

        return event    

    def get_recent_service_events(
        self,
        service_id: int,
        limit: int = 30,
    ) -> list[ServiceEvent]:

        return (
            self.db.query(ServiceEvent)
            .filter(ServiceEvent.service_id == service_id)
            .order_by(ServiceEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )  

    def get_service_by_name(
        self,
        service_name: str,
    ):
        return (
            self.db.query(Service)
            .filter(Service.name == service_name)
            .first()
        )      

    def get_service_health_history(
        self,
        service_id: int,
        limit: int = 30,
    ) -> list[ServiceHealthDaily]:

        return (
            self.db.query(ServiceHealthDaily)
            .filter(ServiceHealthDaily.service_id == service_id)
            .order_by(ServiceHealthDaily.day.desc())
            .limit(limit)
            .all()
        )    