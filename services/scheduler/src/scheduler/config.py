import os

# Redis
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# HTTP health server
HEALTH_PORT: int = int(os.getenv("HEALTH_PORT", "8080"))

# Worker health monitoring
WORKER_HEARTBEAT_TTL: int = int(os.getenv("WORKER_HEARTBEAT_TTL", "60"))
WORKER_HEALTH_CHECK_INTERVAL: int = int(os.getenv("WORKER_HEALTH_CHECK_INTERVAL", "30"))
MIN_HEALTHY_WORKERS: int = int(os.getenv("MIN_HEALTHY_WORKERS", "1"))

# Redis key namespaces
QUEUE_HIGH = "lexbangla:queue:high"
QUEUE_NORMAL = "lexbangla:queue:normal"
QUEUE_LOW = "lexbangla:queue:low"
QUEUE_DEAD = "lexbangla:queue:dead"
WORKER_HEARTBEAT_KEY = "lexbangla:worker:{worker_id}:heartbeat"
WORKER_INFO_KEY = "lexbangla:worker:{worker_id}:info"
WORKERS_INDEX_KEY = "lexbangla:workers"
SCHEDULER_INFO_KEY = "lexbangla:scheduler:info"
JOB_KEY = "lexbangla:job:{job_id}"
JOB_TTL: int = 86400  # 24 hours

# Cron expressions (UTC)
REINGEST_CRON: str = os.getenv("REINGEST_CRON", "0 2 * * *")         # Daily 02:00
PRIORITY_REINGEST_CRON: str = os.getenv("PRIORITY_REINGEST_CRON", "0 */6 * * *")  # Every 6h
FULL_REINDEX_CRON: str = os.getenv("FULL_REINDEX_CRON", "0 3 * * 0")  # Sunday 03:00

# Legal document sources for LexBangla
INGEST_SOURCES = [
    {
        "id": "gazette",
        "name": "Bangladesh Gazette",
        "priority": "high",
        "category": "legislation",
    },
    {
        "id": "supreme_court",
        "name": "Supreme Court Judgments",
        "priority": "high",
        "category": "judgments",
    },
    {
        "id": "hc_division",
        "name": "High Court Division",
        "priority": "normal",
        "category": "judgments",
    },
    {
        "id": "law_commission",
        "name": "Law Commission Reports",
        "priority": "normal",
        "category": "reports",
    },
    {
        "id": "ministry_circulars",
        "name": "Ministry Circulars",
        "priority": "low",
        "category": "circulars",
    },
]
