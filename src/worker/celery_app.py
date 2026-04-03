"""Celery application (Redis broker)."""

from __future__ import annotations

from celery import Celery

from config import celery_broker_url, celery_result_backend, get_settings

settings = get_settings()

app = Celery(
    "kadmoo_video",
    broker=celery_broker_url(settings),
    backend=celery_result_backend(settings),
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="video-jobs",
    task_queues={
        "video-jobs": {
            "exchange": "video-jobs",
            "routing_key": "video-jobs",
        },
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.job_timeout_seconds,
    task_soft_time_limit=max(60, settings.job_timeout_seconds - 60),
)

# Register Celery tasks (after `app` exists)
import worker.tasks  # noqa: E402, I001
