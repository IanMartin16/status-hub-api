from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import ServiceStatus
from app.domain.schemas import (
    ServiceStatusItem,
    StatusResponse,
    StatusSummaryResponse,
    utc_now,
)
from app.repositories.maintenance_repository import MaintenanceRepository
from app.repositories.status_repository import StatusRepository

router = APIRouter(prefix="/v1/status", tags=["status"])


@router.get("", response_model=StatusResponse)
def get_all_status(db: Session = Depends(get_db)) -> StatusResponse:
    repo = StatusRepository(db)
    maintenance_repo = MaintenanceRepository(db)

    services = repo.list_active_services()
    latest_status_map = repo.get_latest_status_map()
    overrides_map = maintenance_repo.get_enabled_overrides_map()

    items: list[ServiceStatusItem] = []
    for service in services:
        override = overrides_map.get(service.id)
        status_row = latest_status_map.get(service.id)

        if override:
            items.append(
                ServiceStatusItem(
                    name=service.name,
                    display_name=service.display_name,
                    status=ServiceStatus.MAINTENANCE,
                    latency_ms=None,
                    last_checked=override.updated_at,
                    message=override.message or "Service under maintenance.",
                )
            )
            continue

        status_value = ServiceStatus.OPERATIONAL
        latency_ms = None
        message = "Pending first real check."

        if status_row:
            status_value = ServiceStatus(status_row.status)
            latency_ms = status_row.latency_ms
            message = status_row.message
            last_checked = status_row.last_checked_at
        else:
            last_checked = utc_now()

        items.append(
            ServiceStatusItem(
                name=service.name,
                display_name=service.display_name,
                status=status_value,
                latency_ms=latency_ms,
                last_checked=last_checked,
                message=message,
            )
        )

    overall_status = ServiceStatus.OPERATIONAL
    if any(s.status == ServiceStatus.DOWN for s in items):
        overall_status = ServiceStatus.DOWN
    elif any(s.status == ServiceStatus.DEGRADED for s in items):
        overall_status = ServiceStatus.DEGRADED
    elif any(s.status == ServiceStatus.MAINTENANCE for s in items):
        overall_status = ServiceStatus.MAINTENANCE

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
            resolved_statuses.append(ServiceStatus.OPERATIONAL)

    operational = sum(1 for s in resolved_statuses if s == ServiceStatus.OPERATIONAL)
    degraded = sum(1 for s in resolved_statuses if s == ServiceStatus.DEGRADED)
    maintenance = sum(1 for s in resolved_statuses if s == ServiceStatus.MAINTENANCE)
    down = sum(1 for s in resolved_statuses if s == ServiceStatus.DOWN)

    overall_status = ServiceStatus.OPERATIONAL
    if down > 0:
        overall_status = ServiceStatus.DOWN
    elif degraded > 0:
        overall_status = ServiceStatus.DEGRADED
    elif maintenance > 0:
        overall_status = ServiceStatus.MAINTENANCE

    return StatusSummaryResponse(
        overall_status=overall_status,
        operational=operational,
        degraded=degraded,
        maintenance=maintenance,
        down=down,
        last_updated=utc_now(),
    )


@router.get("/{service_name}", response_model=ServiceStatusItem)
def get_service_status(service_name: str, db: Session = Depends(get_db)) -> ServiceStatusItem:
    repo = StatusRepository(db)
    maintenance_repo = MaintenanceRepository(db)

    services = repo.list_active_services()
    latest_status_map = repo.get_latest_status_map()
    overrides_map = maintenance_repo.get_enabled_overrides_map()

    for service in services:
        if service.name != service_name:
            continue

        override = overrides_map.get(service.id)
        if override:
            return ServiceStatusItem(
                name=service.name,
                display_name=service.display_name,
                status=ServiceStatus.MAINTENANCE,
                latency_ms=None,
                last_checked=override.updated_at,
                message=override.message or "Service under maintenance.",
            )

        row = latest_status_map.get(service.id)
        if row:
            return ServiceStatusItem(
                name=service.name,
                display_name=service.display_name,
                status=ServiceStatus(row.status),
                latency_ms=row.latency_ms,
                last_checked=row.last_checked_at,
                message=row.message,
            )

        return ServiceStatusItem(
            name=service.name,
            display_name=service.display_name,
            status=ServiceStatus.OPERATIONAL,
            latency_ms=None,
            last_checked=utc_now(),
            message="Pending first real check.",
        )

    raise HTTPException(status_code=404, detail="Service not found")