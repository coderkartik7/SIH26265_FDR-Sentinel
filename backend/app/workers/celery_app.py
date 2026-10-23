"""
Celery application for FDR-Sentinel background task processing.

Tasks:
  - scan_maturity_alerts: Daily scan for FDR maturity thresholds (90/60/30/15/7 days)
  - Periodic escalation of unacknowledged alerts to senior officials
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "fdr_sentinel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Periodic schedule: run maturity scan every day at midnight UTC
celery_app.conf.beat_schedule = {
    "scan-maturity-alerts-daily": {
        "task": "app.workers.tasks.scan_maturity_alerts_task",
        "schedule": crontab(hour=0, minute=0),
    },
}
