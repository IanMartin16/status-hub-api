from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.service import Service  # registers services table in Base.metadata
from app.models.service_check_event import ServiceCheckEvent
from app.models.service_health_daily import ServiceHealthDaily


@dataclass
class DailyAccumulator:
    total_checks: int = 0

    operational_checks: int = 0
    degraded_checks: int = 0
    down_checks: int = 0
    platform_issue_checks: int = 0
    unknown_checks: int = 0

    latency_sum: int = 0
    latency_count: int = 0
    max_latency_ms: int | None = None


def normalize_status(status: str | None) -> str:
    if not status:
        return "unknown"

    normalized = status.strip().lower()

    known_statuses = {
        "operational",
        "degraded",
        "down",
        "platform_issue",
        "unknown",
    }

    if normalized not in known_statuses:
        return "unknown"

    return normalized


def build_daily_aggregates(
    db: Session,
) -> dict[tuple[int, date], DailyAccumulator]:

    result: dict[
        tuple[int, date],
        DailyAccumulator,
    ] = defaultdict(DailyAccumulator)

    events = (
        db.query(ServiceCheckEvent)
        .order_by(
            ServiceCheckEvent.service_id.asc(),
            ServiceCheckEvent.checked_at.asc(),
        )
        .all()
    )

    for event in events:
        day = event.checked_at.date()

        key = (
            event.service_id,
            day,
        )

        accumulator = result[key]

        accumulator.total_checks += 1

        status = normalize_status(event.status)

        if status == "operational":
            accumulator.operational_checks += 1

        elif status == "degraded":
            accumulator.degraded_checks += 1

        elif status == "down":
            accumulator.down_checks += 1

        elif status == "platform_issue":
            accumulator.platform_issue_checks += 1

        else:
            accumulator.unknown_checks += 1

        if event.latency_ms is not None:
            accumulator.latency_sum += event.latency_ms
            accumulator.latency_count += 1

            if (
                accumulator.max_latency_ms is None
                or event.latency_ms > accumulator.max_latency_ms
            ):
                accumulator.max_latency_ms = event.latency_ms

    return result


def upsert_daily_health(
    db: Session,
    aggregates: dict[
        tuple[int, date],
        DailyAccumulator,
    ],
) -> None:

    inserted = 0
    updated = 0

    for (service_id, day), accumulator in aggregates.items():

        existing = (
            db.query(ServiceHealthDaily)
            .filter(
                ServiceHealthDaily.service_id == service_id,
                ServiceHealthDaily.day == day,
            )
            .first()
        )

        availability_pct = (
            accumulator.operational_checks
            / accumulator.total_checks
            * 100
            if accumulator.total_checks
            else None
        )

        avg_latency_ms = (
            accumulator.latency_sum
            / accumulator.latency_count
            if accumulator.latency_count
            else None
        )

        if existing:
            row = existing
            updated += 1
        else:
            row = ServiceHealthDaily(
                service_id=service_id,
                day=day,
            )
            inserted += 1

        row.total_checks = accumulator.total_checks

        row.operational_checks = (
            accumulator.operational_checks
        )

        row.degraded_checks = (
            accumulator.degraded_checks
        )

        row.down_checks = (
            accumulator.down_checks
        )

        row.platform_issue_checks = (
            accumulator.platform_issue_checks
        )

        row.unknown_checks = (
            accumulator.unknown_checks
        )

        row.availability_pct = availability_pct
        row.avg_latency_ms = avg_latency_ms

        row.max_latency_ms = (
            accumulator.max_latency_ms
        )

        db.add(row)

    db.commit()

    print(
        f"Backfill completed: "
        f"{inserted} inserted, "
        f"{updated} updated."
    )


def main():
    db = SessionLocal()

    try:
        aggregates = build_daily_aggregates(db)

        print(
            f"Daily aggregates found: "
            f"{len(aggregates)}"
        )

        upsert_daily_health(
            db,
            aggregates,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()