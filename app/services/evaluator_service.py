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
    PLATFORM_HTTP_STATUSES = {
        408,  # request timeout
        425,  # too early / upstream timing issue
        429,  # rate limited / overload
        499,  # client/proxy closed request
        502,  # bad gateway
        503,  # service unavailable
        504,  # gateway timeout
    }

    HEALTHY_STATUSES = {
        "UP",
        "OK",
        "HEALTHY",
        "OPERATIONAL",
    }

    UNHEALTHY_STATUSES = {
        "DOWN",
        "OUT_OF_SERVICE",
        "ERROR",
        "FAIL",
        "FAILED",
        "UNHEALTHY",
    }

    DEGRADED_STATUSES = {
        "DEGRADED",
        "PARTIAL",
        "PARTIALLY_AVAILABLE",
        "WARNING",
    }

    def evaluate(self, probe: ProbeResult) -> EvaluatedStatus:
        # Caso 1: request falló
        if not probe.ok:
            return self._evaluate_failed_probe(probe)

        # Caso 2: request OK con JSON health payload
        if probe.json_body and isinstance(probe.json_body, dict):
            evaluated_from_payload = self._evaluate_json_payload(probe)

            if evaluated_from_payload:
                return evaluated_from_payload

        # Caso 3: HTTP 2xx pero sin JSON interpretable
        if self._is_slow(probe):
            return EvaluatedStatus(
                status=ServiceStatus.DEGRADED,
                message=(
                    f"Service responded successfully but latency is high "
                    f"({probe.latency_ms} ms)."
                ),
            )

        return EvaluatedStatus(
            status=ServiceStatus.OPERATIONAL,
            message="Service responded successfully.",
        )

    def _evaluate_failed_probe(self, probe: ProbeResult) -> EvaluatedStatus:
        if probe.http_status is not None:
            if probe.http_status in self.PLATFORM_HTTP_STATUSES:
                return EvaluatedStatus(
                    status=ServiceStatus.PLATFORM_ISSUE,
                    message=(
                        f"Possible platform/upstream issue. "
                        f"Service returned HTTP {probe.http_status}."
                    ),
                )

            if 500 <= probe.http_status <= 599:
                return EvaluatedStatus(
                    status=ServiceStatus.DEGRADED,
                    message=f"Service returned server error HTTP {probe.http_status}.",
                )

            if 400 <= probe.http_status <= 499:
                return EvaluatedStatus(
                    status=ServiceStatus.DEGRADED,
                    message=f"Service returned client error HTTP {probe.http_status}.",
                )

            return EvaluatedStatus(
                status=ServiceStatus.UNKNOWN,
                message=f"Service returned unexpected HTTP {probe.http_status}.",
            )

        error = (probe.error or "").lower()

        if "timeout" in error or "timed out" in error:
            return EvaluatedStatus(
                status=ServiceStatus.PLATFORM_ISSUE,
                message=probe.error or "Request timeout detected.",
            )

        if "no healthy upstream" in error:
            return EvaluatedStatus(
                status=ServiceStatus.PLATFORM_ISSUE,
                message=probe.error or "No healthy upstream detected.",
            )

        if "connection refused" in error:
            return EvaluatedStatus(
                status=ServiceStatus.DOWN,
                message=probe.error or "Connection refused.",
            )

        if "name resolution" in error or "dns" in error:
            return EvaluatedStatus(
                status=ServiceStatus.DOWN,
                message=probe.error or "DNS resolution failed.",
            )

        return EvaluatedStatus(
            status=ServiceStatus.DOWN,
            message=probe.error or "Service is down.",
        )

    def _evaluate_json_payload(self, probe: ProbeResult) -> EvaluatedStatus | None:
        raw_status = probe.json_body.get("status")

        if not isinstance(raw_status, str):
            return None

        normalized = raw_status.strip().upper()

        if normalized in self.HEALTHY_STATUSES:
            if self._is_slow(probe):
                return EvaluatedStatus(
                    status=ServiceStatus.DEGRADED,
                    message=(
                        f"Health status {normalized}, but latency is high "
                        f"({probe.latency_ms} ms)."
                    ),
                )

            return EvaluatedStatus(
                status=ServiceStatus.OPERATIONAL,
                message=f"Health status reported as {normalized}.",
            )

        if normalized in self.DEGRADED_STATUSES:
            return EvaluatedStatus(
                status=ServiceStatus.DEGRADED,
                message=f"Health status reported as {normalized}.",
            )

        if normalized in self.UNHEALTHY_STATUSES:
            return EvaluatedStatus(
                status=ServiceStatus.DOWN,
                message=f"Health status reported as {normalized}.",
            )

        return EvaluatedStatus(
            status=ServiceStatus.DEGRADED,
            message=f"Unexpected health status value: {normalized}.",
        )

    def _is_slow(self, probe: ProbeResult) -> bool:
        return (
            probe.latency_ms is not None
            and probe.latency_ms > settings.status_degraded_threshold_ms
        )