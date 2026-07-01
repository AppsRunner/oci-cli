# coding: utf-8
# Copyright (c) 2016, 2026, Oracle and/or its affiliates. All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at
# https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at
# http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

"""Unit tests for AsyncDatabaseRepository."""

from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import oci.exceptions

from packages.database import (
    AsyncDatabaseRepository,
    DatabaseDetails,
    DatabaseSummary,
    RepositoryOperationError,
    ResourceConflictError,
    ResourceNotFoundError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_data(**kwargs):
    """Build a minimal OCI database response stub."""
    defaults = dict(
        id="ocid1.database.oc1..example",
        compartment_id="ocid1.compartment.oc1..example",
        db_name="TESTDB",
        db_unique_name="TESTDB_iad1xz",
        lifecycle_state="AVAILABLE",
        time_created=None,
        freeform_tags={},
        defined_tags={},
        db_workload=None,
        db_version="19.0.0.0",
        character_set=None,
        ncharacter_set=None,
        pdb_name=None,
        db_backup_config=None,
        connection_strings=None,
        kms_key_id=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _oci_response(data, next_page=None):
    resp = MagicMock()
    resp.data = data
    resp.next_page = next_page
    return resp


def _service_error(status: int) -> oci.exceptions.ServiceError:
    return oci.exceptions.ServiceError(
        status=status,
        code="ServiceError",
        headers={},
        message=f"Simulated {status} error",
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _passthrough_call(fn, *args, **kwargs):
    """Replacement for _call that executes fn directly (no executor)."""
    return fn(*args, **kwargs)


async def _raising_call(fn, *args, **kwargs):
    """Replacement for _call that executes fn and translates ServiceErrors."""
    try:
        return fn(*args, **kwargs)
    except oci.exceptions.ServiceError as exc:
        AsyncDatabaseRepository._translate_service_error(exc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAsyncDatabaseRepositoryGet(unittest.TestCase):
    def setUp(self):
        self.config = {"region": "us-ashburn-1"}

    def _make_repo(self, mock_client):
        repo = AsyncDatabaseRepository(self.config)
        repo._executor = MagicMock()
        repo._client = mock_client
        return repo

    def test_get_returns_database_details(self):
        mock_client = MagicMock()
        data = _make_db_data()
        mock_client.get_database.return_value = _oci_response(data)

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_passthrough_call):
            result = run(repo.get("ocid1.database.oc1..example"))

        self.assertIsInstance(result, DatabaseDetails)
        self.assertEqual(result.id, "ocid1.database.oc1..example")
        self.assertEqual(result.lifecycle_state, "AVAILABLE")
        self.assertEqual(result.db_version, "19.0.0.0")

    def test_get_raises_resource_not_found_on_404(self):
        mock_client = MagicMock()
        mock_client.get_database.side_effect = _service_error(404)

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_raising_call):
            with self.assertRaises(ResourceNotFoundError):
                run(repo.get("ocid1.database.oc1..missing"))

    def test_get_raises_repository_operation_error_on_500(self):
        mock_client = MagicMock()
        mock_client.get_database.side_effect = _service_error(500)

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_raising_call):
            with self.assertRaises(RepositoryOperationError):
                run(repo.get("ocid1.database.oc1..error"))


class TestAsyncDatabaseRepositoryList(unittest.TestCase):
    def setUp(self):
        self.config = {"region": "us-ashburn-1"}

    def _make_repo(self, mock_client):
        repo = AsyncDatabaseRepository(self.config)
        repo._executor = MagicMock()
        repo._client = mock_client
        return repo

    def test_list_returns_summaries(self):
        mock_client = MagicMock()
        items = [_make_db_data(id=f"ocid1.db.{i}") for i in range(3)]
        mock_client.list_databases.return_value = _oci_response(items, next_page=None)

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_passthrough_call):
            result = run(repo.list("ocid1.compartment.oc1..example"))

        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], DatabaseSummary)
        self.assertEqual(result[0].id, "ocid1.db.0")

    def test_list_follows_pagination(self):
        mock_client = MagicMock()
        page1 = [_make_db_data(id="ocid1.db.0")]
        page2 = [_make_db_data(id="ocid1.db.1")]
        mock_client.list_databases.side_effect = [
            _oci_response(page1, next_page="token-abc"),
            _oci_response(page2, next_page=None),
        ]

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_passthrough_call):
            result = run(repo.list("ocid1.compartment.oc1..example"))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, "ocid1.db.0")
        self.assertEqual(result[1].id, "ocid1.db.1")

    def test_list_passes_filters(self):
        mock_client = MagicMock()
        mock_client.list_databases.return_value = _oci_response([], next_page=None)

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_passthrough_call):
            run(repo.list("ocid1.compartment.oc1..example", lifecycle_state="AVAILABLE"))

        _, kwargs = mock_client.list_databases.call_args
        self.assertEqual(kwargs.get("lifecycle_state"), "AVAILABLE")


class TestAsyncDatabaseRepositoryDelete(unittest.TestCase):
    def setUp(self):
        self.config = {"region": "us-ashburn-1"}

    def _make_repo(self, mock_client):
        repo = AsyncDatabaseRepository(self.config)
        repo._executor = MagicMock()
        repo._client = mock_client
        return repo

    def test_delete_calls_client(self):
        mock_client = MagicMock()
        mock_client.delete_database.return_value = None

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_passthrough_call):
            result = run(repo.delete("ocid1.database.oc1..example"))

        self.assertIsNone(result)
        mock_client.delete_database.assert_called_once_with("ocid1.database.oc1..example")

    def test_delete_raises_conflict_on_409(self):
        mock_client = MagicMock()
        mock_client.delete_database.side_effect = _service_error(409)

        repo = self._make_repo(mock_client)
        with patch.object(repo, "_call", new=_raising_call):
            with self.assertRaises(ResourceConflictError):
                run(repo.delete("ocid1.database.oc1..locked"))


class TestAsyncDatabaseRepositoryLifecycle(unittest.TestCase):
    def setUp(self):
        self.config = {"region": "us-ashburn-1"}

    def test_ensure_open_raises_when_closed(self):
        repo = AsyncDatabaseRepository(self.config)
        with self.assertRaises(RuntimeError):
            repo._ensure_open()

    def test_open_and_close(self):
        with patch("packages.database.async_repository.oci.database.DatabaseClient"):
            repo = AsyncDatabaseRepository(self.config)
            repo.open()
            self.assertIsNotNone(repo._executor)
            self.assertIsNotNone(repo._client)
            repo.close()
            self.assertIsNone(repo._executor)

    def test_context_manager(self):
        with patch("packages.database.async_repository.oci.database.DatabaseClient"):
            async def _run():
                async with AsyncDatabaseRepository(self.config) as repo:
                    self.assertIsNotNone(repo._executor)
                self.assertIsNone(repo._executor)

            run(_run())

    def test_workers_default(self):
        repo = AsyncDatabaseRepository(self.config)
        self.assertEqual(repo._workers, 4)

    def test_workers_custom(self):
        repo = AsyncDatabaseRepository(self.config, workers=8)
        self.assertEqual(repo._workers, 8)


class TestTranslateServiceError(unittest.TestCase):
    def test_404_raises_resource_not_found(self):
        with self.assertRaises(ResourceNotFoundError):
            AsyncDatabaseRepository._translate_service_error(_service_error(404))

    def test_409_raises_resource_conflict(self):
        with self.assertRaises(ResourceConflictError):
            AsyncDatabaseRepository._translate_service_error(_service_error(409))

    def test_500_raises_repository_operation_error(self):
        with self.assertRaises(RepositoryOperationError):
            AsyncDatabaseRepository._translate_service_error(_service_error(500))


if __name__ == "__main__":
    unittest.main()
