import os
import socket

# Redis
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Worker identity
WORKER_ID: str = os.getenv("WORKER_ID", socket.gethostname())
WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", "1"))

# Heartbeat
HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "15"))   # seconds
HEARTBEAT_TTL: int = int(os.getenv("HEARTBEAT_TTL", "60"))             # Redis key TTL

# Queue keys (must match scheduler config)
QUEUE_HIGH = "lexbangla:queue:high"
QUEUE_NORMAL = "lexbangla:queue:normal"
QUEUE_LOW = "lexbangla:queue:low"
QUEUE_DEAD = "lexbangla:queue:dead"
QUEUES_ORDERED = [QUEUE_HIGH, QUEUE_NORMAL, QUEUE_LOW]

# Redis keys
WORKER_HEARTBEAT_KEY = "lexbangla:worker:{worker_id}:heartbeat"
WORKER_INFO_KEY = "lexbangla:worker:{worker_id}:info"
WORKERS_INDEX_KEY = "lexbangla:workers"
JOB_KEY = "lexbangla:job:{job_id}"
JOB_TTL: int = 86400

# Task processing
TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "300"))   # seconds per task
BRPOP_TIMEOUT: int = int(os.getenv("BRPOP_TIMEOUT", "5"))   # blocking pop wait
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
