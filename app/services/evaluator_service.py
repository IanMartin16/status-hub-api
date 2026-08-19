from typing import Any

from app.core.config import settings
from app.domain.enums import ServiceStatus
from app.domain.schemas import ProbeResult


class EvaluatedStatus:
    def __init__(
        self,
        status: ServiceStatus,
        message: str | None,
        readiness: str | None = None,
        uptime_seconds: int | None = None,
        contract_version: str | None = None,
        checks: list[dict[str, Any]] | None = None,
    ):
        self.status = status
        self.message = message

        self.readiness = readiness
        self.uptime_seconds = uptime_seconds
        self.contract_version = contract_version
        self.checks = checks


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
        # Caso 1:
        # Si existe un payload JSON interpretable, darle prioridad.
        # Esto permite conservar health.v1 incluso si responde 503.
        if probe.json_body and isinstance(probe.json_body, dict):
            evaluated_from_payload = self._evaluate_json_payload(probe)

            if evaluated_from_payload:
                return evaluated_from_payload

        # Caso 2: request falló y no hubo health payload interpretable
        if not probe.ok:
            return self._evaluate_failed_probe(probe)

        # Caso 3: HTTP 2xx pero sin JSON health interpretable
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

    def _evaluate_json_payload(
        self,
        probe: ProbeResult,
    ) -> EvaluatedStatus | None:

        body = probe.json_body or {}

        raw_status = body.get("status")

        if not isinstance(raw_status, str):
            return None

        normalized = raw_status.strip().upper()

        telemetry = self._extract_health_v1_telemetry(probe)

        if normalized in self.HEALTHY_STATUSES:
            # Si health.v1 dice operational pero el HTTP no fue exitoso,
            # existe una inconsistencia que conviene representar como degraded.
            if not probe.ok:
                return EvaluatedStatus(
                    status=ServiceStatus.DEGRADED,
                    message=(
                        f"Health status reported as {normalized}, "
                        f"but endpoint returned HTTP {probe.http_status}."
                    ),
                    **telemetry,
                )

            if self._is_slow(probe):
                return EvaluatedStatus(
                    status=ServiceStatus.DEGRADED,
                    message=(
                        f"Health status {normalized}, but latency is high "
                        f"({probe.latency_ms} ms)."
                    ),
                    **telemetry,
                )

            return EvaluatedStatus(
                status=ServiceStatus.OPERATIONAL,
                message=f"Health status reported as {normalized}.",
                **telemetry,
            )

        if normalized in self.DEGRADED_STATUSES:
            return EvaluatedStatus(
                status=ServiceStatus.DEGRADED,
                message=f"Health status reported as {normalized}.",
                **telemetry,
            )

        if normalized in self.UNHEALTHY_STATUSES:
            return EvaluatedStatus(
                status=ServiceStatus.DOWN,
                message=f"Health status reported as {normalized}.",
                **telemetry,
            )

        return EvaluatedStatus(
            status=ServiceStatus.DEGRADED,
            message=f"Unexpected health status value: {normalized}.",
            **telemetry,
        )

    def _is_slow(self, probe: ProbeResult) -> bool:
        return (
            probe.latency_ms is not None
            and probe.latency_ms > settings.status_degraded_threshold_ms
        )

    def _extract_health_v1_telemetry(
        self,
        probe: ProbeResult,
    ) -> dict[str, Any]:

        body = probe.json_body or {}

        contract_version = body.get("contract_version")

        if contract_version != "health.v1":
            return {
                "readiness": None,
                "uptime_seconds": None,
                "contract_version": None,
                "checks": None,
            }

        readiness = body.get("readiness")

        if not isinstance(readiness, str):
            readiness = None

        uptime_seconds = body.get("uptime_seconds")

        if (
            not isinstance(uptime_seconds, int)
            or isinstance(uptime_seconds, bool)
            or uptime_seconds < 0
        ):
            uptime_seconds = None

        raw_checks = body.get("checks")
        checks: list[dict[str, Any]] | None = None

        # Forma 1:
        # [
        #   {"name": "database", "status": "operational"}
        # ]
        if isinstance(raw_checks, list):
            checks = [
                item
                for item in raw_checks
                if isinstance(item, dict)
            ]

        # Forma 2:
        # {
        #   "database": {"status": "operational"}
        # }
        elif isinstance(raw_checks, dict):
            checks = []

            for name, value in raw_checks.items():
                if not isinstance(value, dict):
                    continue

                normalized_check = {
                    "name": name,
                    **value,
                }

                checks.append(normalized_check)

        return {
            "readiness": readiness,
            "uptime_seconds": uptime_seconds,
            "contract_version": contract_version,
            "checks": checks,
        }   