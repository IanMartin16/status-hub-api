from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import ServiceStatus
from app.domain.schemas import (
    ServiceCheckEventItem,
    ServiceEventItem,
    ServiceEventsResponse,
    ServiceStatusItem,
    StatusResponse,
    StatusSummaryResponse,
    ServiceHealthDailyItem,
    ServiceHistoryResponse,
    utc_now,
)
from app.repositories.maintenance_repository import MaintenanceRepository
from app.repositories.status_repository import StatusRepository

router = APIRouter(prefix="/v1/status", tags=["status"])


def resolve_overall_status(statuses: list[ServiceStatus]) -> ServiceStatus:
    """
    Priority:
    down > platform_issue > degraded > maintenance > unknown > operational
    """
    if any(s == ServiceStatus.DOWN for s in statuses):
        return ServiceStatus.DOWN

    if any(s == ServiceStatus.PLATFORM_ISSUE for s in statuses):
        return ServiceStatus.PLATFORM_ISSUE

    if any(s == ServiceStatus.DEGRADED for s in statuses):
        return ServiceStatus.DEGRADED

    if any(s == ServiceStatus.MAINTENANCE for s in statuses):
        return ServiceStatus.MAINTENANCE

    if any(s == ServiceStatus.UNKNOWN for s in statuses):
        return ServiceStatus.UNKNOWN

    return ServiceStatus.OPERATIONAL


def build_recent_events(events) -> list[ServiceCheckEventItem]:
    """
    Repo returns newest -> oldest.
    Frontend bars need oldest -> newest.
    """
    return [
        ServiceCheckEventItem(
            status=ServiceStatus(event.status),
            latency_ms=event.latency_ms,
            http_status=event.http_status,
            checked_at=event.checked_at,
            message=event.message,
        )
        for event in reversed(events)
    ]


@router.get("", response_model=StatusResponse)
def get_all_status(db: Session = Depends(get_db)) -> StatusResponse:
    repo = StatusRepository(db)
    maintenance_repo = MaintenanceRepository(db)

    services = repo.list_active_services()
    latest_status_map = repo.get_latest_status_map()
    overrides_map = maintenance_repo.get_enabled_overrides_map()

    service_ids = [service.id for service in services]
    events_map = repo.get_recent_events_map(service_ids, limit_per_service=30)

    items: list[ServiceStatusItem] = []

    for service in services:
        override = overrides_map.get(service.id)
        status_row = latest_status_map.get(service.id)
        recent_events = build_recent_events(events_map.get(service.id, []))

        if override:
            items.append(
                ServiceStatusItem(
                    name=service.name,
                    display_name=service.display_name,
                    status=ServiceStatus.MAINTENANCE,
                    latency_ms=None,
                    http_status=None,

                    readiness=None,
                    uptime_seconds=None,
                    contract_version=None,
                    checks=None,

                    last_checked=override.updated_at,
                    last_status_change_at=override.updated_at,
                    consecutive_failures=0,
                    message=override.message or "Service under maintenance.",
                    recent_events=recent_events,
                )
            )
            continue

        if status_row:
            items.append(
                ServiceStatusItem(
                    name=service.name,
                    display_name=service.display_name,
                    status=ServiceStatus(status_row.status),
                    latency_ms=status_row.latency_ms,
                    http_status=status_row.http_status,

                    readiness=status_row.readiness,
                    uptime_seconds=status_row.uptime_seconds,
                    contract_version=status_row.contract_version,
                    checks=status_row.checks,

                    last_checked=status_row.last_checked_at,
                    last_status_change_at=status_row.last_status_change_at,
                    consecutive_failures=status_row.consecutive_failures,
                    message=status_row.message,
                    recent_events=recent_events,
                )
            )
            continue

        items.append(
            ServiceStatusItem(
                name=service.name,
                display_name=service.display_name,
                status=ServiceStatus.UNKNOWN,
                latency_ms=None,
                http_status=None,

                readiness=None,
                uptime_seconds=None,
                contract_version=None,
                checks=None,

                last_checked=utc_now(),
                last_status_change_at=None,
                consecutive_failures=0,
                message="Pending first real check.",
                recent_events=recent_events,
            )
        )

    overall_status = resolve_overall_status([item.status for item in items])

    return StatusResponse(
        overall_status=overall_status,
        last_updated=utc_now(),
        services=items,
    )


@router.get("/summary", response_model=StatusSummaryResponse)
def get_status_summary(db: Session = Depends(get_db)) -> StatusSummaryResponse:
    repo = StatusRepository(db)
    maintenance_repo = MaintenanceRepository(db)

    services = repo.list_active_services()
    latest_status_map = repo.get_latest_status_map()
    overrides_map = maintenance_repo.get_enabled_overrides_map()

    resolved_statuses: list[ServiceStatus] = []

    for service in services:
        override = overrides_map.get(service.id)

        if override:
            resolved_statuses.append(ServiceStatus.MAINTENANCE)
            continue

        row = latest_status_map.get(service.id)

        if row:
            resolved_statuses.append(ServiceStatus(row.status))
        else:
            resolved_statuses.append(ServiceStatus.UNKNOWN)

    operational = sum(1 for s in resolved_statuses if s == ServiceStatus.OPERATIONAL)
    degraded = sum(1 for s in resolved_statuses if s == ServiceStatus.DEGRADED)
    maintenance = sum(1 for s in resolved_statuses if s == ServiceStatus.MAINTENANCE)
    down = sum(1 for s in resolved_statuses if s == ServiceStatus.DOWN)
    platform_issue = sum(1 for s in resolved_statuses if s == ServiceStatus.PLATFORM_ISSUE)
    unknown = sum(1 for s in resolved_statuses if s == ServiceStatus.UNKNOWN)

    overall_status = resolve_overall_status(resolved_statuses)

    return StatusSummaryResponse(
        overall_status=overall_status,
        operational=operational,
        degraded=degraded,
        maintenance=maintenance,
        down=down,
        platform_issue=platform_issue,
        unknown=unknown,
        last_updated=utc_now(),
    )


@router.get("/{service_name}", response_model=ServiceStatusItem)
def get_service_status(
    service_name: str,
    db: Session = Depends(get_db),
) -> ServiceStatusItem:
    repo = StatusRepository(db)
    maintenance_repo = MaintenanceRepository(db)

    services = repo.list_active_services()
    latest_status_map = repo.get_latest_status_map()
    overrides_map = maintenance_repo.get_enabled_overrides_map()

    for service in services:
        if service.name != service_name:
            continue

        events = repo.get_recent_events_by_service(service.id, limit=30)
        recent_events = build_recent_events(events)

        override = overrides_map.get(service.id)

        if override:
            return ServiceStatusItem(
                name=service.name,
                display_name=service.display_name,
                status=ServiceStatus.MAINTENANCE,
                latency_ms=None,
                http_status=None,
                last_checked=override.updated_at,
                last_status_change_at=override.updated_at,
                consecutive_failures=0,
                message=override.message or "Service under maintenance.",
                recent_events=recent_events,
            )

        row = latest_status_map.get(service.id)

        if row:
            return ServiceStatusItem(
                name=service.name,
                display_name=service.display_name,
                status=ServiceStatus(row.status),
                latency_ms=row.latency_ms,
                http_status=row.http_status,
                readiness=row.readiness,
                uptime_seconds=row.uptime_seconds,
                contract_version=row.contract_version,
                checks=row.checks,
                last_checked=row.last_checked_at,
                last_status_change_at=row.last_status_change_at,
                consecutive_failures=row.consecutive_failures,
                message=row.message,
                recent_events=recent_events,
            )

        return ServiceStatusItem(
            name=service.name,
            display_name=service.display_name,
            status=ServiceStatus.UNKNOWN,
            latency_ms=None,
            http_status=None,
            last_checked=utc_now(),
            last_status_change_at=None,
            consecutive_failures=0,
            message="Pending first real check.",
            recent_events=recent_events,
        )

    raise HTTPException(status_code=404, detail="Service not found")

@router.get(
    "/{service_name}/events",
    response_model=ServiceEventsResponse,
)
def get_service_events(
    service_name: str,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ServiceEventsResponse:

    repo = StatusRepository(db)

    services = repo.list_active_services()

    for service in services:
        if service.name != service_name:
            continue

        rows = repo.get_recent_service_events(
            service_id=service.id,
            limit=limit,
        )

        events = [
            ServiceEventItem(
                event_type=row.event_type,
                severity=row.severity,
                previous_status=row.previous_status,
                current_status=row.current_status,
                message=row.message,
                metadata=row.event_metadata,
                source_check_id=row.source_check_id,
                occurred_at=row.occurred_at,
            )
            for row in rows
        ]

        return ServiceEventsResponse(
            name=service.name,
            display_name=service.display_name,
            events=events,
        )

    raise HTTPException(
        status_code=404,
        detail="Service not found",
    )    

@router.get(
    "/{service_name}/history",
    response_model=ServiceHistoryResponse,
)
def get_service_history(
    service_name: str,
    limit: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
) -> ServiceHistoryResponse:

    repo = StatusRepository(db)

    service = repo.get_service_by_name(service_name)

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    rows = repo.get_service_health_history(
        service_id=service.id,
        limit=limit,
    )

    history = [
        ServiceHealthDailyItem(
            day=row.day,
            total_checks=row.total_checks,
            operational_checks=row.operational_checks,
            degraded_checks=row.degraded_checks,
            down_checks=row.down_checks,
            platform_issue_checks=row.platform_issue_checks,
            unknown_checks=row.unknown_checks,
            availability_pct=row.availability_pct,
            avg_latency_ms=row.avg_latency_ms,
            max_latency_ms=row.max_latency_ms,
        )
        for row in rows
    ]

    return ServiceHistoryResponse(
        name=service.name,
        display_name=service.display_name,
        history=history,
    )    