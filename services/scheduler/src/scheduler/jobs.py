import logging
from datetime import date

from scheduler import config
from scheduler.queue_client import QueueClient

logger = logging.getLogger(__name__)


def enqueue_daily_reingest(queue: QueueClient) -> None:
    """Enqueue re-ingestion tasks for all configured sources."""
    today = date.today().isoformat()
    enqueued = 0
    for source in config.INGEST_SOURCES:
        queue.enqueue(
            task_type="ingest",
            payload={"source_id": source["id"], "date": today, "category": source["category"]},
            priority=source["priority"],
        )
        enqueued += 1
    logger.info("Daily re-ingest: enqueued %d tasks for %s", enqueued, today)


def enqueue_priority_reingest(queue: QueueClient) -> None:
    """Enqueue re-ingestion for high-priority sources only (runs every 6 hours)."""
    today = date.today().isoformat()
    enqueued = 0
    for source in config.INGEST_SOURCES:
        if source["priority"] == "high":
            queue.enqueue(
                task_type="ingest",
                payload={
                    "source_id": source["id"],
                    "date": today,
                    "category": source["category"],
                    "reason": "priority_refresh",
                },
                priority="high",
            )
            enqueued += 1
    logger.info("Priority re-ingest: enqueued %d high-priority tasks", enqueued)


def enqueue_full_reindex(queue: QueueClient) -> None:
    """Enqueue a full reindex task for all document categories (runs weekly)."""
    categories = list({s["category"] for s in config.INGEST_SOURCES})
    for category in categories:
        queue.enqueue(
            task_type="reindex",
            payload={"category": category, "full": True},
            priority="low",
        )
    logger.info("Full reindex: enqueued tasks for categories %s", categories)
