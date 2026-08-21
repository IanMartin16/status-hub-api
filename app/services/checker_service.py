from sqlalchemy.orm import Session

from app.clients.http_probe_client import HttpProbeClient
from app.repositories.status_repository import StatusRepository
from app.services.evaluator_service import EvaluatorService
from app.services.event_detector_service import EventDetectorService

import logging

logger = logging.getLogger(__name__)

class CheckerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StatusRepository(db)
        self.probe_client = HttpProbeClient()
        self.evaluator = EvaluatorService()
        self.event_detector = EventDetectorService()

    def run_checks(self) -> None:
        services = self.repo.list_active_services()

        for service in services:
            try:
                previous = self.repo.get_status_by_service_id(
                    service.id
                )

                previous_status = (
                    previous.status
                    if previous
                    else None
                )

                previous_readiness = (
                    previous.readiness
                    if previous
                    else None
                )

                previous_uptime_seconds = (
                    previous.uptime_seconds
                    if previous
                    else None
                )

                probe = self.probe_client.probe(
                    service.health_url
                )

                evaluated = self.evaluator.evaluate(probe)

                self.repo.upsert_status(
                    service_id=service.id,
                    status=evaluated.status.value,
                    latency_ms=probe.latency_ms,
                    http_status=probe.http_status,
                    message=evaluated.message,
                    raw_error=probe.error,
                    readiness=evaluated.readiness,
                    uptime_seconds=evaluated.uptime_seconds,
                    contract_version=evaluated.contract_version,
                    checks=evaluated.checks,
                )

                check_event = self.repo.insert_check_event(
                    service_id=service.id,
                    status=evaluated.status.value,
                    latency_ms=probe.latency_ms,
                    http_status=probe.http_status,
                    message=evaluated.message,
                    raw_error=probe.error,
                    readiness=evaluated.readiness,
                    uptime_seconds=evaluated.uptime_seconds,
                    contract_version=evaluated.contract_version,
                    checks=evaluated.checks,
                )

                # Obtiene check_event.id sin cerrar
                # la transacción.
                self.db.flush()

                detected_events = self.event_detector.detect(
                    previous_status=previous_status,
                    current_status=evaluated.status.value,
                    previous_readiness=previous_readiness,
                    current_readiness=evaluated.readiness,
                    previous_uptime_seconds=(
                        previous_uptime_seconds
                    ),
                    current_uptime_seconds=(
                        evaluated.uptime_seconds
                    ),
                )

                for detected in detected_events:
                    self.repo.insert_service_event(
                        service_id=service.id,
                        event_type=detected.event_type,
                        severity=detected.severity,
                        previous_status=(
                            detected.previous_status
                        ),
                        current_status=(
                            detected.current_status
                        ),
                        message=detected.message,
                        event_metadata=detected.metadata,
                        source_check_id=check_event.id,
                    )

                self.db.commit()

            except Exception:
                self.db.rollback()

                logger.exception(
                    "Internal status check failure for service=%s",
                    service.name,
                )

                continue