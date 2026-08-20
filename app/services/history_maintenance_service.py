from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.service_check_event import ServiceCheckEvent
from app.models.service_health_daily import ServiceHealthDaily
from app.models.service import Service


class HistoryMaintenanceService:
    RETENTION_DAYS = 60

    def __init__(self, db: Session):
        self.db = db

    def run(self) -> dict:
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        self.rollup_day(yesterday)
        deleted_checks = self.apply_retention()

        self.db.commit()

        return {
            "rolled_up_day": str(yesterday),
            "deleted_checks": deleted_checks,
        }

    def rollup_day(self, day) -> None:
        start = datetime.combine(
            day,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        end = start + timedelta(days=1)

        rows = (
            self.db.query(ServiceCheckEvent)
            .filter(
                ServiceCheckEvent.checked_at >= start,
                ServiceCheckEvent.checked_at < end,
            )
            .all()
        )

        grouped: dict[int, list[ServiceCheckEvent]] = {}

        for row in rows:
            grouped.setdefault(row.service_id, []).append(row)

        for service_id, events in grouped.items():
            total_checks = len(events)

            operational = sum(
                1 for e in events if e.status == "operational"
            )
            degraded = sum(
                1 for e in events if e.status == "degraded"
            )
            down = sum(
                1 for e in events if e.status == "down"
            )
            platform_issue = sum(
                1 for e in events if e.status == "platform_issue"
            )
            unknown = sum(
                1 for e in events if e.status == "unknown"
            )

            latencies = [
                e.latency_ms
                for e in events
                if e.latency_ms is not None
            ]

            available_checks = operational + degraded

            known_checks = (
                operational
                + degraded
                + down
                + platform_issue
            )

            availability_pct = (
                (available_checks / known_checks) * 100
                if known_checks
                else 0.0
            )

            avg_latency_ms = (
                sum(latencies) / len(latencies)
                if latencies
                else None
            )

            max_latency_ms = max(latencies) if latencies else None

            existing = (
                self.db.query(ServiceHealthDaily)
                .filter(
                    ServiceHealthDaily.service_id == service_id,
                    ServiceHealthDaily.day == day,
                )
                .first()
            )

            if existing:
                existing.total_checks = total_checks
                existing.operational_checks = operational
                existing.degraded_checks = degraded
                existing.down_checks = down
                existing.platform_issue_checks = platform_issue
                existing.unknown_checks = unknown
                existing.availability_pct = availability_pct
                existing.avg_latency_ms = avg_latency_ms
                existing.max_latency_ms = max_latency_ms
            else:
                self.db.add(
                    ServiceHealthDaily(
                        service_id=service_id,
                        day=day,
                        total_checks=total_checks,
                        operational_checks=operational,
                        degraded_checks=degraded,
                        down_checks=down,
                        platform_issue_checks=platform_issue,
                        unknown_checks=unknown,
                        availability_pct=availability_pct,
                        avg_latency_ms=avg_latency_ms,
                        max_latency_ms=max_latency_ms,
                    )
                )

    def apply_retention(self) -> int:
        today = datetime.now(timezone.utc).date()
        cutoff_day = today - timedelta(days=self.RETENTION_DAYS)

        cutoff = datetime.combine(
            cutoff_day,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        old_events = (
            self.db.query(ServiceCheckEvent)
            .filter(ServiceCheckEvent.checked_at < cutoff)
            .all()
        )

        deleted = 0

        for event in old_events:
            event_day = event.checked_at.date()

            aggregate_exists = (
                self.db.query(ServiceHealthDaily.id)
                .filter(
                    ServiceHealthDaily.service_id == event.service_id,
                    ServiceHealthDaily.day == event_day,
                )
                .first()
                is not None
            )

            if aggregate_exists:
                self.db.delete(event)
                deleted += 1

        return deleted