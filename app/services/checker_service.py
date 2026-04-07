from sqlalchemy.orm import Session

from app.clients.http_probe_client import HttpProbeClient
from app.repositories.status_repository import StatusRepository
from app.services.evaluator_service import EvaluatorService


class CheckerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StatusRepository(db)
        self.probe_client = HttpProbeClient()
        self.evaluator = EvaluatorService()

    def run_checks(self) -> None:
        services = self.repo.list_active_services()

        for service in services:
            probe = self.probe_client.probe(service.health_url)
            evaluated = self.evaluator.evaluate(probe)

            self.repo.upsert_status(
                service_id=service.id,
                status=evaluated.status.value,
                latency_ms=probe.latency_ms,
                http_status=probe.http_status,
                message=evaluated.message,
                raw_error=probe.error,
            )