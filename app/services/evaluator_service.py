from app.core.config import settings
from app.domain.enums import ServiceStatus
from app.domain.schemas import ProbeResult


class EvaluatedStatus:
    def __init__(
        self,
        status: ServiceStatus,
        message: str | None,
    ):
        self.status = status
        self.message = message


class EvaluatorService:
    def evaluate(self, probe: ProbeResult) -> EvaluatedStatus:
        if not probe.ok:
            if probe.http_status is not None:
                return EvaluatedStatus(
                    status=ServiceStatus.DOWN,
                    message=f"Service returned HTTP {probe.http_status}.",
                )

            return EvaluatedStatus(
                status=ServiceStatus.DOWN,
                message=probe.error or "Service is down.",
            )

        # Interpretación por JSON health payload
        if probe.json_body and isinstance(probe.json_body, dict):
            raw_status = probe.json_body.get("status")

            if isinstance(raw_status, str):
                normalized = raw_status.strip().upper()

                if normalized in {"UP", "OK", "HEALTHY", "OPERATIONAL"}:
                    if probe.latency_ms is not None and probe.latency_ms > settings.status_degraded_threshold_ms:
                        return EvaluatedStatus(
                            status=ServiceStatus.DEGRADED,
                            message=f"Health status {normalized}, but latency is high ({probe.latency_ms} ms).",
                        )

                    return EvaluatedStatus(
                        status=ServiceStatus.OPERATIONAL,
                        message=f"Health status reported as {normalized}.",
                    )

                if normalized in {"DOWN", "OUT_OF_SERVICE", "ERROR", "FAIL"}:
                    return EvaluatedStatus(
                        status=ServiceStatus.DOWN,
                        message=f"Health status reported as {normalized}.",
                    )

                return EvaluatedStatus(
                    status=ServiceStatus.DEGRADED,
                    message=f"Unexpected health status value: {normalized}.",
                )

        # Fallback: si HTTP fue 2xx pero no había JSON interpretable
        if probe.latency_ms is not None and probe.latency_ms > settings.status_degraded_threshold_ms:
            return EvaluatedStatus(
                status=ServiceStatus.DEGRADED,
                message=f"Service responded successfully but latency is high ({probe.latency_ms} ms).",
            )

        return EvaluatedStatus(
            status=ServiceStatus.OPERATIONAL,
            message="Service responded successfully.",
        )