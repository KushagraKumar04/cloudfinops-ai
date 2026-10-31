import logging
from typing import Any, Callable

from redis import Redis
from rq import Queue

from app.config import get_settings

logger = logging.getLogger("app.workers")


def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def get_queue() -> Queue:
    settings = get_settings()
    return Queue(settings.worker_queue_name, connection=get_redis())


def enqueue_task(func: Callable, *args: Any, **kwargs: Any) -> Any:
    settings = get_settings()

    if not settings.worker_enabled:
        logger.info("Worker disabled. Running %s inline", func.__name__)
        return func(*args, **kwargs)

    queue = get_queue()
    job = queue.enqueue(
        func,
        *args,
        job_timeout=settings.worker_job_timeout_seconds,
        result_ttl=settings.worker_result_ttl_seconds,
        **kwargs,
    )
    logger.info("Enqueued %s as job %s", func.__name__, job.id)
    return job