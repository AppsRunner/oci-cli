import logging
import sys

import redis

from worker import config
from worker.worker import Worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("LexBangla Worker starting (id=%s)", config.WORKER_ID)

    redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
    try:
        redis_client.ping()
        logger.info("Connected to Redis at %s", config.REDIS_URL)
    except redis.ConnectionError as exc:
        logger.critical("Cannot connect to Redis: %s", exc)
        sys.exit(1)

    worker = Worker(redis_client)
    worker.start()


if __name__ == "__main__":
    main()
