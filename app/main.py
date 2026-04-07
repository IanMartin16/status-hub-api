from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes_admin import router as admin_router
from app.api.routes_health import router as health_router
from app.api.routes_status import router as status_router
from app.bootstrap.seed_services import seed_services
from app.core.config import settings
from app.core.scheduler import StatusHubScheduler
from app.db.base import Base
from app.db.session import engine, SessionLocal

from app.models.maintenance_override import MaintenanceOverride
from app.models.service import Service
from app.models.service_status import ServiceStatusRecord
from app.services.checker_service import CheckerService

status_hub_scheduler = StatusHubScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        seed_services(db)

        checker = CheckerService(db)
        checker.run_checks()
    finally:
        db.close()

    status_hub_scheduler.start()

    yield

    status_hub_scheduler.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(status_router)
app.include_router(admin_router)