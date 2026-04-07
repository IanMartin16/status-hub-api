from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel

from app.domain.enums import ServiceStatus


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime


class ServiceStatusItem(BaseModel):
    name: str
    display_name: str
    status: ServiceStatus
    latency_ms: int | None = None
    last_checked: datetime
    message: str | None = None


class StatusResponse(BaseModel):
    overall_status: ServiceStatus
    last_updated: datetime
    services: list[ServiceStatusItem]


class StatusSummaryResponse(BaseModel):
    overall_status: ServiceStatus
    operational: int
    degraded: int
    maintenance: int
    down: int
    last_updated: datetime


class ProbeResult(BaseModel):
    ok: bool
    latency_ms: int | None = None
    http_status: int | None = None
    error: str | None = None
    json_body: dict[str, Any] | None = None
    text_body: str | None = None


class MaintenanceRequest(BaseModel):
    enabled: bool
    message: str | None = None


class MaintenanceResponse(BaseModel):
    service_name: str
    enabled: bool
    message: str | None = None
    updated_at: datetime


def utc_now() -> datetime:
    return datetime.now(timezone.utc)