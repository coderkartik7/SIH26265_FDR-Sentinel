"""
Celery tasks for FDR-Sentinel.
"""
import logging
from app.workers.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="app.workers.tasks.scan_maturity_alerts_task", bind=True, max_retries=3)
def scan_maturity_alerts_task(self):
    """
    Daily Celery Beat task: scans all active FDR cases for maturity thresholds
    (90, 60, 30, 15, 7 days) and auto-escalates unacknowledged alerts.
    """
    from app.services.alert_service import scan_maturity_alerts_and_escalate
    db = SessionLocal()
    try:
        result = scan_maturity_alerts_and_escalate(db)
        logger.info(f"Maturity alert scan complete: {result}")
        return result
    except Exception as exc:
        logger.exception("Error in scan_maturity_alerts_task")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
