from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.checker_service import CheckerService


class StatusHubScheduler:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(timezone="UTC")

    def run_checks_job(self) -> None:
        db = SessionLocal()
        try:
            checker = CheckerService(db)
            checker.run_checks()
        finally:
            db.close()

    def start(self) -> None:
        if self.scheduler.running:
            return

        self.scheduler.add_job(
            func=self.run_checks_job,
            trigger=IntervalTrigger(seconds=settings.status_check_interval_seconds),
            id="status-hub-checks",
            name="Status Hub periodic checks",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)