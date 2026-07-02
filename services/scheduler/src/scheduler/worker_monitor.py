import json
import logging
from datetime import datetime, timezone
from typing import Dict, List

import redis

from scheduler import config

logger = logging.getLogger(__name__)


class WorkerMonitor:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def registered_workers(self) -> List[str]:
        raw = self._redis.smembers(config.WORKERS_INDEX_KEY)
        return [w.decode() if isinstance(w, bytes) else w for w in raw]

    def worker_info(self, worker_id: str) -> Dict:
        key = config.WORKER_INFO_KEY.format(worker_id=worker_id)
        raw = self._redis.get(key)
        if raw is None:
            return {}
        return json.loads(raw)

    def is_alive(self, worker_id: str) -> bool:
        key = config.WORKER_HEARTBEAT_KEY.format(worker_id=worker_id)
        return self._redis.exists(key) > 0

    def healthy_workers(self) -> List[str]:
        return [w for w in self.registered_workers() if self.is_alive(w)]

    def stale_workers(self) -> List[str]:
        return [w for w in self.registered_workers() if not self.is_alive(w)]

    def check_and_alert(self) -> Dict:
        all_workers = self.registered_workers()
        alive = self.healthy_workers()
        stale = self.stale_workers()

        status = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "total_registered": len(all_workers),
            "healthy": len(alive),
            "stale": stale,
            "healthy_workers": alive,
        }

        if stale:
            logger.warning("Stale workers detected (no heartbeat): %s", stale)
            self._remove_stale(stale)

        if len(alive) < config.MIN_HEALTHY_WORKERS:
            logger.error(
                "Insufficient healthy workers: %d alive, minimum required is %d",
                len(alive),
                config.MIN_HEALTHY_WORKERS,
            )

        return status

    def _remove_stale(self, stale_ids: List[str]) -> None:
        for worker_id in stale_ids:
            self._redis.srem(config.WORKERS_INDEX_KEY, worker_id)
            logger.info("Removed stale worker %s from registry", worker_id)
