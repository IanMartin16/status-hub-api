from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.domain.schemas import MaintenanceRequest, MaintenanceResponse
from app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def verify_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post(
    "/services/{service_name}/maintenance",
    response_model=MaintenanceResponse,
    dependencies=[Depends(verify_admin_token)],
)
def set_service_maintenance(
    service_name: str,
    request: MaintenanceRequest,
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    service = MaintenanceService(db).set_maintenance(
        service_name=service_name,
        enabled=request.enabled,
        message=request.message,
    )

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return MaintenanceResponse(
        service_name=service_name,
        enabled=service.enabled,
        message=service.message,
        updated_at=service.updated_at,
    )