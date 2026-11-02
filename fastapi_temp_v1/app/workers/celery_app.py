from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "fastapi_temp_v1",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Acknowledge tasks after execution.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Email tasks do not need to return results.
    task_ignore_result=True,

    # Protect the worker from tasks that hang.
    task_soft_time_limit=60,
    task_time_limit=90,

    # Retry broker publishing when Redis is temporarily unavailable.
    task_publish_retry=True,
    task_publish_retry_policy={
        "max_retries": 3,
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 2,
    },
)