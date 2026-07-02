import json
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Any, Dict

import redis

from worker import config
from worker.heartbeat import Heartbeat
from worker.tasks import ingest, reindex

logger = logging.getLogger(__name__)

_TASK_HANDLERS = {
    "ingest": ingest.run,
    "reindex": reindex.run,
}


class Worker:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client
        self._heartbeat = Heartbeat(redis_client, config.WORKER_ID)
        self._running = False

    def start(self) -> None:
        self._heartbeat.start(metadata={
            "worker_id": config.WORKER_ID,
            "queues": config.QUEUES_ORDERED,
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        self._heartbeat.beat()

        self._running = True
        self._register_signals()

        logger.info(
            "Worker %s listening on queues: %s",
            config.WORKER_ID,
            config.QUEUES_ORDERED,
        )

        try:
            self._loop()
        finally:
            self._shutdown()

    def _loop(self) -> None:
        while self._running:
            result = self._redis.brpop(config.QUEUES_ORDERED, timeout=config.BRPOP_TIMEOUT)
            if result is None:
                continue  # timeout with no message; loop and check _running

            _queue_key, raw = result
            try:
                message: Dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.error("Malformed message dropped: %s (%s)", raw[:200], exc)
                continue

            self._process(message)

    def _process(self, message: Dict[str, Any]) -> None:
        job_id = message.get("job_id", "unknown")
        task_type = message.get("task_type")
        payload = message.get("payload", {})
        retry_count = message.get("retry_count", 0)
        max_retries = message.get("max_retries", config.MAX_RETRIES)

        self._update_job(job_id, status="running")
        logger.info("Processing job=%s type=%s retry=%d", job_id, task_type, retry_count)

        handler = _TASK_HANDLERS.get(task_type)
        if handler is None:
            logger.error("Unknown task_type '%s' for job %s", task_type, job_id)
            self._update_job(job_id, status="failed", error=f"unknown task type: {task_type}")
            self._dead_letter(message, f"unknown task type: {task_type}")
            return

        try:
            result = handler(payload)
            self._update_job(job_id, status="completed", result=result)
            logger.info("Completed job=%s result=%s", job_id, result)
        except Exception as exc:
            logger.exception("Job %s failed (attempt %d/%d): %s", job_id, retry_count + 1, max_retries, exc)
            if retry_count < max_retries:
                self._retry(message, retry_count + 1)
            else:
                self._update_job(job_id, status="failed", error=str(exc))
                self._dead_letter(message, str(exc))

    def _retry(self, message: Dict[str, Any], new_retry_count: int) -> None:
        message["retry_count"] = new_retry_count
        queue_key = config.QUEUE_NORMAL  # retry on normal priority
        self._redis.lpush(queue_key, json.dumps(message))
        logger.info("Requeued job=%s for retry %d", message.get("job_id"), new_retry_count)

    def _dead_letter(self, message: Dict[str, Any], error: str) -> None:
        message["failed_at"] = datetime.now(timezone.utc).isoformat()
        message["error"] = error
        self._redis.lpush(config.QUEUE_DEAD, json.dumps(message))

    def _update_job(self, job_id: str, status: str, result: Any = None, error: str = "") -> None:
        key = config.JOB_KEY.format(job_id=job_id)
        update = {
            "status": status,
            "worker_id": config.WORKER_ID,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if result is not None:
            update["result"] = json.dumps(result)
        if error:
            update["error"] = error
        try:
            self._redis.hset(key, mapping=update)
            self._redis.expire(key, config.JOB_TTL)
        except Exception as exc:
            logger.warning("Could not update job metadata for %s: %s", job_id, exc)

    def _shutdown(self) -> None:
        logger.info("Worker %s shutting down", config.WORKER_ID)
        self._heartbeat.stop()

    def _register_signals(self) -> None:
        def handle(sig, frame):
            logger.info("Received signal %s", sig)
            self._running = False

        signal.signal(signal.SIGTERM, handle)
        signal.signal(signal.SIGINT, handle)
