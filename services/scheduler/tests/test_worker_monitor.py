from unittest.mock import MagicMock

import pytest

from scheduler import config
from scheduler.worker_monitor import WorkerMonitor


@pytest.fixture()
def redis_mock():
    return MagicMock()


@pytest.fixture()
def monitor(redis_mock):
    return WorkerMonitor(redis_mock)


class TestRegisteredWorkers:
    def test_returns_decoded_worker_ids(self, monitor, redis_mock):
        redis_mock.smembers.return_value = {b"worker-1", b"worker-2"}
        result = monitor.registered_workers()
        assert set(result) == {"worker-1", "worker-2"}

    def test_returns_empty_when_no_workers(self, monitor, redis_mock):
        redis_mock.smembers.return_value = set()
        assert monitor.registered_workers() == []


class TestIsAlive:
    def test_alive_when_heartbeat_key_exists(self, monitor, redis_mock):
        redis_mock.exists.return_value = 1
        assert monitor.is_alive("worker-1") is True

    def test_dead_when_heartbeat_key_missing(self, monitor, redis_mock):
        redis_mock.exists.return_value = 0
        assert monitor.is_alive("worker-1") is False


class TestHealthyAndStale:
    def test_healthy_workers_are_alive(self, monitor, redis_mock):
        redis_mock.smembers.return_value = {"w1", "w2", "w3"}
        redis_mock.exists.side_effect = lambda key: 1 if "w1" in key else 0
        assert monitor.healthy_workers() == ["w1"]

    def test_stale_workers_have_no_heartbeat(self, monitor, redis_mock):
        redis_mock.smembers.return_value = {"w1", "w2"}
        redis_mock.exists.return_value = 0
        assert set(monitor.stale_workers()) == {"w1", "w2"}


class TestCheckAndAlert:
    def test_removes_stale_workers(self, monitor, redis_mock):
        redis_mock.smembers.return_value = {"w1"}
        redis_mock.exists.return_value = 0  # w1 is stale

        monitor.check_and_alert()

        redis_mock.srem.assert_called_once_with(config.WORKERS_INDEX_KEY, "w1")

    def test_returns_status_dict(self, monitor, redis_mock):
        redis_mock.smembers.return_value = {"w1"}
        redis_mock.exists.return_value = 1  # w1 is alive

        status = monitor.check_and_alert()

        assert status["healthy"] == 1
        assert status["total_registered"] == 1
        assert status["stale"] == []
