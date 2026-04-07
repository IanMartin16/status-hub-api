from sqlalchemy.orm import Session

from app.models.maintenance_override import MaintenanceOverride
from app.models.service import Service


class MaintenanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_service_by_name(self, service_name: str) -> Service | None:
        return self.db.query(Service).filter(Service.name == service_name).first()

    def get_override_by_service_id(self, service_id: int) -> MaintenanceOverride | None:
        return (
            self.db.query(MaintenanceOverride)
            .filter(MaintenanceOverride.service_id == service_id)
            .first()
        )

    def get_enabled_overrides_map(self) -> dict[int, MaintenanceOverride]:
        rows = (
            self.db.query(MaintenanceOverride)
            .filter(MaintenanceOverride.enabled.is_(True))
            .all()
        )
        return {row.service_id: row for row in rows}

    def upsert_override(
        self,
        service_id: int,
        enabled: bool,
        message: str | None,
    ) -> MaintenanceOverride:
        existing = self.get_override_by_service_id(service_id)

        if existing:
            existing.enabled = enabled
            existing.message = message
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        created = MaintenanceOverride(
            service_id=service_id,
            enabled=enabled,
            message=message,
        )
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created