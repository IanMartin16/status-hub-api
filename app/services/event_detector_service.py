from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectedEvent:
    event_type: str
    severity: str
    previous_status: str | None = None
    current_status: str | None = None
    message: str | None = None
    metadata: dict[str, Any] | None = field(default=None)


class EventDetectorService:
    FAILURE_STATUSES = {
        "degraded",
        "down",
        "platform_issue",
        "unknown",
    }

    def detect(
        self,
        *,
        previous_status: str | None,
        current_status: str,
        previous_readiness: str | None,
        current_readiness: str | None,
        previous_uptime_seconds: int | None,
        current_uptime_seconds: int | None,
    ) -> list[DetectedEvent]:
        events: list[DetectedEvent] = []

        # 1. Status transitions
        if (
            previous_status is not None
            and previous_status != current_status
        ):
            if current_status == "degraded":
                events.append(
                    DetectedEvent(
                        event_type="SERVICE_DEGRADED",
                        severity="warning",
                        previous_status=previous_status,
                        current_status=current_status,
                        message=(
                            f"Service changed from "
                            f"{previous_status} to degraded."
                        ),
                    )
                )

            elif current_status == "down":
                events.append(
                    DetectedEvent(
                        event_type="SERVICE_DOWN",
                        severity="critical",
                        previous_status=previous_status,
                        current_status=current_status,
                        message=(
                            f"Service changed from "
                            f"{previous_status} to down."
                        ),
                    )
                )

            elif current_status == "platform_issue":
                events.append(
                    DetectedEvent(
                        event_type="PLATFORM_ISSUE",
                        severity="warning",
                        previous_status=previous_status,
                        current_status=current_status,
                        message=(
                            f"Service changed from "
                            f"{previous_status} to platform_issue."
                        ),
                    )
                )

            elif (
                current_status == "operational"
                and previous_status in self.FAILURE_STATUSES
            ):
                events.append(
                    DetectedEvent(
                        event_type="SERVICE_RECOVERED",
                        severity="info",
                        previous_status=previous_status,
                        current_status=current_status,
                        message=(
                            f"Service recovered from "
                            f"{previous_status}."
                        ),
                    )
                )

        # 2. Readiness transitions
        # NULL means "no previous health.v1 baseline":
        # do not generate fake migration events.
        if (
            previous_readiness is not None
            and current_readiness is not None
            and previous_readiness != current_readiness
        ):
            if current_readiness == "not_ready":
                events.append(
                    DetectedEvent(
                        event_type="READINESS_LOST",
                        severity="warning",
                        previous_status=previous_status,
                        current_status=current_status,
                        message="Service lost readiness.",
                        metadata={
                            "previous_readiness": previous_readiness,
                            "current_readiness": current_readiness,
                        },
                    )
                )

            elif (
                previous_readiness == "not_ready"
                and current_readiness == "ready"
            ):
                events.append(
                    DetectedEvent(
                        event_type="READINESS_RECOVERED",
                        severity="info",
                        previous_status=previous_status,
                        current_status=current_status,
                        message="Service readiness recovered.",
                        metadata={
                            "previous_readiness": previous_readiness,
                            "current_readiness": current_readiness,
                        },
                    )
                )

        # 3. Restart detection
        if (
            previous_uptime_seconds is not None
            and current_uptime_seconds is not None
            and current_uptime_seconds < previous_uptime_seconds
        ):
            events.append(
                DetectedEvent(
                    event_type="SERVICE_RESTARTED",
                    severity="info",
                    previous_status=previous_status,
                    current_status=current_status,
                    message="Service restart detected from uptime reset.",
                    metadata={
                        "previous_uptime_seconds": previous_uptime_seconds,
                        "current_uptime_seconds": current_uptime_seconds,
                    },
                )
            )

        return events