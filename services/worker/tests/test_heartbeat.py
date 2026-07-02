from unittest.mock import ANY, MagicMock

import pytest

from worker import config
from worker.heartbeat import Heartbeat


@pytest.fixture()
def redis_mock():
    return MagicMock()


@pytest.fixture()
def hb(redis_mock):
    return Heartbeat(redis_mock, "test-worker")


class TestBeat:
    def test_sets_key_with_ttl(self, hb, redis_mock):
        hb.beat()
        expected_key = config.WORKER_HEARTBEAT_KEY.format(worker_id="test-worker")
        call_args = redis_mock.set.call_args
        assert call_args[0][0] == expected_key
        assert isinstance(call_args[0][1], str)  # ISO timestamp
        assert call_args[1]["ex"] == config.HEARTBEAT_TTL


class TestStart:
    def test_registers_worker_in_index(self, hb, redis_mock):
        hb.start()
        redis_mock.sadd.assert_called_once_with(config.WORKERS_INDEX_KEY, "test-worker")

    def test_stores_metadata_when_provided(self, hb, redis_mock):
        meta = {"worker_id": "test-worker", "queues": ["q1"]}
        hb.start(metadata=meta)
        expected_key = config.WORKER_INFO_KEY.format(worker_id="test-worker")
        set_calls = redis_mock.set.call_args_list
        keys_set = [c[0][0] for c in set_calls]
        assert expected_key in keys_set


class TestStop:
    def test_deregisters_worker(self, hb, redis_mock):
        hb.start()
        hb.stop()
        redis_mock.srem.assert_called_once_with(config.WORKERS_INDEX_KEY, "test-worker")

    def test_deletes_heartbeat_and_info_keys(self, hb, redis_mock):
        hb.start()
        hb.stop()
        hb_key = config.WORKER_HEARTBEAT_KEY.format(worker_id="test-worker")
        info_key = config.WORKER_INFO_KEY.format(worker_id="test-worker")
        redis_mock.delete.assert_called_once_with(hb_key, info_key)
