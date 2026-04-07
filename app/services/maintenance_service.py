from sqlalchemy.orm import Session

from app.repositories.maintenance_repository import MaintenanceRepository


class MaintenanceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MaintenanceRepository(db)

    def set_maintenance(
        self,
        service_name: str,
        enabled: bool,
        message: str | None,
    ):
        service = self.repo.get_service_by_name(service_name)
        if not service:
            return None

        return self.repo.upsert_override(
            service_id=service.id,
            enabled=enabled,
            message=message,
        )