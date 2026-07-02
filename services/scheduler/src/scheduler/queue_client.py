import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

from scheduler import config

logger = logging.getLogger(__name__)

_PRIORITY_TO_QUEUE = {
    "high": config.QUEUE_HIGH,
    "normal": config.QUEUE_NORMAL,
    "low": config.QUEUE_LOW,
}


class QueueClient:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: str = "normal",
        max_retries: int = 3,
        job_id: Optional[str] = None,
    ) -> str:
        if priority not in _PRIORITY_TO_QUEUE:
            raise ValueError(f"Unknown priority '{priority}'; must be high/normal/low")

        job_id = job_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        message = {
            "job_id": job_id,
            "task_type": task_type,
            "payload": payload,
            "priority": priority,
            "created_at": now,
            "retry_count": 0,
            "max_retries": max_retries,
        }

        queue_key = _PRIORITY_TO_QUEUE[priority]
        self._redis.lpush(queue_key, json.dumps(message))

        job_meta_key = config.JOB_KEY.format(job_id=job_id)
        self._redis.hset(job_meta_key, mapping={
            "job_id": job_id,
            "task_type": task_type,
            "priority": priority,
            "status": "queued",
            "created_at": now,
        })
        self._redis.expire(job_meta_key, config.JOB_TTL)

        logger.info("Enqueued %s job %s on %s queue", task_type, job_id, priority)
        return job_id

    def dead_letter(self, message: Dict[str, Any], error: str) -> None:
        message["failed_at"] = datetime.now(timezone.utc).isoformat()
        message["error"] = error
        self._redis.lpush(config.QUEUE_DEAD, json.dumps(message))
        logger.warning("Moved job %s to dead-letter queue: %s", message.get("job_id"), error)

    def queue_lengths(self) -> Dict[str, int]:
        return {
            "high": self._redis.llen(config.QUEUE_HIGH),
            "normal": self._redis.llen(config.QUEUE_NORMAL),
            "low": self._redis.llen(config.QUEUE_LOW),
            "dead": self._redis.llen(config.QUEUE_DEAD),
        }
