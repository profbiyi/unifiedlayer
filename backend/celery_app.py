"""
Celery Application Configuration.

Initializes the Celery app with Redis as broker and result backend.
"""
from celery import Celery

from backend.config import settings

# Create Celery application
celery_app = Celery(
    "unifiedlayer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "backend.tasks.dbt_tasks",
        "backend.tasks.health_checks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Tasks acknowledged after execution (safer for retries)
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours

    # Worker settings
    worker_prefetch_multiplier=1,  # Don't prefetch many tasks (for long-running tasks)
    worker_concurrency=4,  # Number of concurrent workers

    # Task routes (optional, for task prioritization)
    task_routes={
        "backend.tasks.dbt_tasks.*": {"queue": "dbt"},
        "backend.tasks.health_checks.*": {"queue": "health"},
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule (for periodic tasks, if needed)
    beat_schedule={},
)


# Optional: Task base class with common behavior
class BaseTask(celery_app.Task):
    """Base task class with common error handling."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Task {self.name}[{task_id}] failed: {exc}", exc_info=True)
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Task {self.name}[{task_id}] retrying: {exc}")
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Task {self.name}[{task_id}] completed successfully")
        super().on_success(retval, task_id, args, kwargs)
