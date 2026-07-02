import json
import logging
import signal
import sys
from datetime import datetime, timezone

import redis
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from scheduler import config
from scheduler.health_server import HealthServer
from scheduler.jobs import (
    enqueue_daily_reingest,
    enqueue_full_reindex,
    enqueue_priority_reingest,
)
from scheduler.queue_client import QueueClient
from scheduler.worker_monitor import WorkerMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _parse_cron(expr: str) -> CronTrigger:
    parts = expr.split()
    return CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone="UTC",
    )


def main() -> None:
    logger.info("LexBangla Scheduler starting up")

    redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
    try:
        redis_client.ping()
        logger.info("Connected to Redis at %s", config.REDIS_URL)
    except redis.ConnectionError as exc:
        logger.critical("Cannot connect to Redis: %s", exc)
        sys.exit(1)

    queue = QueueClient(redis_client)
    monitor = WorkerMonitor(redis_client)

    redis_client.set(
        config.SCHEDULER_INFO_KEY,
        json.dumps({"started_at": datetime.now(timezone.utc).isoformat(), "pid": __import__("os").getpid()}),
    )

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=enqueue_daily_reingest,
        trigger=_parse_cron(config.REINGEST_CRON),
        id="daily_reingest",
        name="Daily re-ingestion of all sources",
        kwargs={"queue": queue},
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.add_job(
        func=enqueue_priority_reingest,
        trigger=_parse_cron(config.PRIORITY_REINGEST_CRON),
        id="priority_reingest",
        name="Priority source refresh every 6h",
        kwargs={"queue": queue},
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        func=enqueue_full_reindex,
        trigger=_parse_cron(config.FULL_REINDEX_CRON),
        id="full_reindex",
        name="Weekly full reindex",
        kwargs={"queue": queue},
        replace_existing=True,
        misfire_grace_time=1800,
    )

    worker_health_cache: dict = {}

    def run_worker_health_check() -> None:
        result = monitor.check_and_alert()
        worker_health_cache.update(result)

    scheduler.add_job(
        func=run_worker_health_check,
        trigger="interval",
        seconds=config.WORKER_HEALTH_CHECK_INTERVAL,
        id="worker_health_check",
        name="Worker health monitor",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started with %d jobs: %s",
        len(scheduler.get_jobs()),
        [j.id for j in scheduler.get_jobs()],
    )

    def get_status() -> dict:
        return health_server.build_status(
            scheduler_running=scheduler.running,
            worker_status=worker_health_cache,
            queue_lengths=queue.queue_lengths(),
        )

    health_server = HealthServer(port=config.HEALTH_PORT, get_status=get_status)
    health_server.start()

    shutdown_requested = False

    def handle_signal(sig, frame) -> None:
        nonlocal shutdown_requested
        logger.info("Received signal %s, shutting down…", sig)
        shutdown_requested = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("Scheduler running. Health endpoint: http://0.0.0.0:%d/health", config.HEALTH_PORT)

    import time
    while not shutdown_requested:
        time.sleep(1)

    logger.info("Shutting down scheduler")
    scheduler.shutdown(wait=False)
    health_server.stop()
    redis_client.delete(config.SCHEDULER_INFO_KEY)
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
