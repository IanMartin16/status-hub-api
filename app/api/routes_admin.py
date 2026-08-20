from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.domain.schemas import MaintenanceRequest, MaintenanceResponse, ServiceEventsResponse
from app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def verify_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


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

    service = repo.get_service_by_name(service_name)

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

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