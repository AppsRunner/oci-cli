import json
import logging
import threading
from datetime import datetime, timezone

import redis

from worker import config

logger = logging.getLogger(__name__)


class Heartbeat:
    """Periodically writes a Redis key so the scheduler can detect live workers."""

    def __init__(self, redis_client: redis.Redis, worker_id: str) -> None:
        self._redis = redis_client
        self._worker_id = worker_id
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self, metadata: dict | None = None) -> None:
        self._redis.sadd(config.WORKERS_INDEX_KEY, self._worker_id)
        if metadata:
            info_key = config.WORKER_INFO_KEY.format(worker_id=self._worker_id)
            self._redis.set(info_key, json.dumps(metadata), ex=config.HEARTBEAT_TTL * 5)

        self._thread = threading.Thread(target=self._loop, daemon=True, name="heartbeat")
        self._thread.start()
        logger.info("Heartbeat started for worker %s (interval=%ds)", self._worker_id, config.HEARTBEAT_INTERVAL)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=config.HEARTBEAT_INTERVAL + 1)
        self._deregister()

    def beat(self) -> None:
        key = config.WORKER_HEARTBEAT_KEY.format(worker_id=self._worker_id)
        self._redis.set(key, datetime.now(timezone.utc).isoformat(), ex=config.HEARTBEAT_TTL)

    def _loop(self) -> None:
        while not self._stop_event.wait(timeout=config.HEARTBEAT_INTERVAL):
            try:
                self.beat()
            except Exception as exc:
                logger.warning("Heartbeat write failed: %s", exc)

    def _deregister(self) -> None:
        try:
            self._redis.srem(config.WORKERS_INDEX_KEY, self._worker_id)
            hb_key = config.WORKER_HEARTBEAT_KEY.format(worker_id=self._worker_id)
            info_key = config.WORKER_INFO_KEY.format(worker_id=self._worker_id)
            self._redis.delete(hb_key, info_key)
            logger.info("Worker %s deregistered from Redis", self._worker_id)
        except Exception as exc:
            logger.warning("Deregistration error: %s", exc)
