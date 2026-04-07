from fastapi import APIRouter
from app.core.config import settings
from app.domain.schemas import HealthResponse, utc_now

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=utc_now(),
    )