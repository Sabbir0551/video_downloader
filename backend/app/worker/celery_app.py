import os
from celery import Celery

from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "anystream_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Execution timeouts (Defense against infinite streams / hangup attacks)
    task_time_limit=600,       # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    # Worker concurrency & reliability
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=1800,       # 30 minutes
    task_default_queue="media_downloads",
    task_routes={
        "app.worker.tasks.download_media_task": {"queue": "media_downloads"},
        "app.worker.tasks.*": {"queue": "media_downloads"},
    },
    # Periodic Celery Beat Schedule (Janitor file cleanup)
    beat_schedule={
        "clean-expired-downloads-every-5-minutes": {
            "task": "app.worker.tasks.clean_expired_downloads_task",
            "schedule": settings.FILE_CLEANUP_INTERVAL_SECONDS,  # 300s (5 minutes)
        },
    },
)

# Auto-discover tasks from app.worker.tasks
celery_app.autodiscover_tasks(["app.worker"])

