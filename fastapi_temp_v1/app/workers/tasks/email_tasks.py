import logging

from celery import Task

from app.core.config import get_settings
from app.services.email_service import (
    PermanentEmailError,
    TemporaryEmailError,
    send_verification_email,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    name="app.workers.tasks.email_tasks.send_verification_email_task",
    ignore_result=True,
)
def send_verification_email_task(
    self: Task,
    recipient: str,
    full_name: str,
    token: str,
) -> None:
    try:
        send_verification_email(
            recipient=recipient,
            full_name=full_name,
            token=token,
        )

    except PermanentEmailError:
        logger.exception(
            "Permanent email delivery failure. task_id=%s",
            self.request.id,
        )
        # Permanent failures should not be retried automatically.
        raise

    except TemporaryEmailError as exc:
        retries = self.request.retries

        if retries >= settings.celery_task_max_retries:
            logger.exception(
                "Email delivery exhausted retries. task_id=%s",
                self.request.id,
            )
            raise

        countdown = settings.celery_task_retry_delay_seconds * (
            2 ** retries
        )

        logger.warning(
            "Temporary email delivery failure; retrying. "
            "task_id=%s retry=%s",
            self.request.id,
            retries + 1,
        )

        raise self.retry(
            exc=exc,
            countdown=countdown,
            max_retries=settings.celery_task_max_retries,
        ) from exc

    except Exception as exc:
        # Unknown failures may be transient, so retry a bounded number
        # of times. The raw exception and task arguments are not logged.
        retries = self.request.retries

        if retries >= settings.celery_task_max_retries:
            logger.exception(
                "Unexpected email task failure after retries. task_id=%s",
                self.request.id,
            )
            raise

        countdown = settings.celery_task_retry_delay_seconds * (
            2 ** retries
        )

        logger.exception(
            "Unexpected email task failure; retrying. task_id=%s",
            self.request.id,
        )

        raise self.retry(
            exc=exc,
            countdown=countdown,
            max_retries=settings.celery_task_max_retries,
        ) from exc

    logger.info(
        "Verification email processed successfully. task_id=%s",
        self.request.id,
    )