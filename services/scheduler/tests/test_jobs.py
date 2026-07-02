import json
from unittest.mock import MagicMock, call, patch

import pytest

from scheduler import config
from scheduler.jobs import (
    enqueue_daily_reingest,
    enqueue_full_reindex,
    enqueue_priority_reingest,
)
from scheduler.queue_client import QueueClient


@pytest.fixture()
def redis_mock():
    m = MagicMock()
    m.lpush = MagicMock()
    m.hset = MagicMock()
    m.expire = MagicMock()
    return m


@pytest.fixture()
def queue(redis_mock):
    return QueueClient(redis_mock)


class TestEnqueueDailyReingest:
    def test_enqueues_all_sources(self, queue, redis_mock):
        enqueue_daily_reingest(queue)
        assert redis_mock.lpush.call_count == len(config.INGEST_SOURCES)

    def test_message_contains_source_id(self, queue, redis_mock):
        enqueue_daily_reingest(queue)
        pushed_messages = [
            json.loads(redis_mock.lpush.call_args_list[i][0][1])
            for i in range(len(config.INGEST_SOURCES))
        ]
        source_ids = {m["payload"]["source_id"] for m in pushed_messages}
        expected = {s["id"] for s in config.INGEST_SOURCES}
        assert source_ids == expected

    def test_task_type_is_ingest(self, queue, redis_mock):
        enqueue_daily_reingest(queue)
        for call_args in redis_mock.lpush.call_args_list:
            msg = json.loads(call_args[0][1])
            assert msg["task_type"] == "ingest"


class TestEnqueuePriorityReingest:
    def test_enqueues_only_high_priority_sources(self, queue, redis_mock):
        enqueue_priority_reingest(queue)
        high_priority_count = sum(1 for s in config.INGEST_SOURCES if s["priority"] == "high")
        assert redis_mock.lpush.call_count == high_priority_count

    def test_all_messages_go_to_high_queue(self, queue, redis_mock):
        enqueue_priority_reingest(queue)
        for call_args in redis_mock.lpush.call_args_list:
            queue_key = call_args[0][0]
            assert queue_key == config.QUEUE_HIGH


class TestEnqueueFullReindex:
    def test_enqueues_one_task_per_category(self, queue, redis_mock):
        enqueue_full_reindex(queue)
        categories = {s["category"] for s in config.INGEST_SOURCES}
        assert redis_mock.lpush.call_count == len(categories)

    def test_all_tasks_are_reindex_type(self, queue, redis_mock):
        enqueue_full_reindex(queue)
        for call_args in redis_mock.lpush.call_args_list:
            msg = json.loads(call_args[0][1])
            assert msg["task_type"] == "reindex"

    def test_full_flag_is_set(self, queue, redis_mock):
        enqueue_full_reindex(queue)
        for call_args in redis_mock.lpush.call_args_list:
            msg = json.loads(call_args[0][1])
            assert msg["payload"]["full"] is True
