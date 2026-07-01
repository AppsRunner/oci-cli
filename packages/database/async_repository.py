# coding: utf-8
# Copyright (c) 2016, 2026, Oracle and/or its affiliates. All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at
# https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at
# http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

"""Async Repository implementation backed by the OCI Database service."""

from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import oci
import oci.exceptions

from .exceptions import (
    RepositoryOperationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from .models import DatabaseDetails, DatabaseSummary
from .repository import Repository

_DEFAULT_WORKERS = 4


def _run_sync(loop: asyncio.AbstractEventLoop, executor: ThreadPoolExecutor, fn, *args, **kwargs):
    """Schedule a blocking call in *executor* and return an awaitable."""
    return loop.run_in_executor(executor, functools.partial(fn, *args, **kwargs))


class AsyncDatabaseRepository(Repository[DatabaseDetails, DatabaseSummary]):
    """Async repository that wraps the OCI :class:`oci.database.DatabaseClient`.

    The OCI Python SDK provides only synchronous clients. This class offloads
    every blocking SDK call to a thread-pool executor so callers can ``await``
    them without blocking the event loop.

    Example::

        config = oci.config.from_file()
        async with AsyncDatabaseRepository(config) as repo:
            db = await repo.get("ocid1.database.oc1...")
            databases = await repo.list("ocid1.compartment.oc1...")
    """

    def __init__(
        self,
        config: dict[str, Any],
        *,
        workers: int = _DEFAULT_WORKERS,
        client_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._config = config
        self._workers = workers
        self._client_kwargs: dict[str, Any] = client_kwargs or {}
        self._executor: ThreadPoolExecutor | None = None
        self._client: oci.database.DatabaseClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ------------------------------------------------------------------
    # Context-manager helpers
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AsyncDatabaseRepository":
        self.open()
        return self

    async def __aexit__(self, *_: Any) -> None:
        self.close()

    def open(self) -> None:
        """Initialise the executor and OCI client.  Called implicitly by ``async with``."""
        self._executor = ThreadPoolExecutor(max_workers=self._workers)
        self._client = oci.database.DatabaseClient(self._config, **self._client_kwargs)

    def close(self) -> None:
        """Shut down the executor.  Called implicitly by ``async with``."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_open(self) -> tuple[ThreadPoolExecutor, oci.database.DatabaseClient]:
        if self._executor is None or self._client is None:
            raise RuntimeError(
                "Repository is not open.  Use 'async with AsyncDatabaseRepository(...)' or call open() first."
            )
        return self._executor, self._client

    async def _call(self, fn, *args, **kwargs):
        """Run a synchronous OCI SDK call in the thread executor."""
        executor, _ = self._ensure_open()
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                executor, functools.partial(fn, *args, **kwargs)
            )
            return response
        except oci.exceptions.ServiceError as exc:
            self._translate_service_error(exc)
            raise  # unreachable; _translate always raises

    @staticmethod
    def _translate_service_error(exc: oci.exceptions.ServiceError) -> None:
        if exc.status == 404:
            raise ResourceNotFoundError(
                getattr(exc, "target_service", "unknown"), "database"
            ) from exc
        if exc.status == 409:
            raise ResourceConflictError(str(exc)) from exc
        raise RepositoryOperationError(str(exc), cause=exc) from exc

    # ------------------------------------------------------------------
    # Repository interface
    # ------------------------------------------------------------------

    async def get(self, resource_id: str) -> DatabaseDetails:
        """Return full details for a single database by OCID."""
        _, client = self._ensure_open()
        response = await self._call(client.get_database, resource_id)
        return DatabaseDetails.from_oci_response(response.data)

    async def list(self, compartment_id: str, **filters: Any) -> list[DatabaseSummary]:
        """Return all databases in *compartment_id*.

        Accepted *filters* (passed directly to the OCI ``list_databases`` call):
        - ``db_home_id`` – restrict to a specific DB Home
        - ``system_id`` – restrict to a specific DB System
        - ``lifecycle_state`` – e.g. ``"AVAILABLE"``
        - ``limit`` / ``page`` – pagination controls
        """
        _, client = self._ensure_open()
        summaries: list[DatabaseSummary] = []
        page: str | None = None

        while True:
            kwargs: dict[str, Any] = {"compartment_id": compartment_id, **filters}
            if page:
                kwargs["page"] = page

            response = await self._call(client.list_databases, **kwargs)
            summaries.extend(
                DatabaseSummary.from_oci_response(item) for item in response.data
            )

            next_page = response.next_page
            if not next_page:
                break
            page = next_page

        return summaries

    async def create(self, compartment_id: str, details: dict[str, Any]) -> DatabaseDetails:
        """Create a new database inside an existing DB Home.

        *details* must include at minimum:
        - ``db_home_id`` – OCID of the target DB Home
        - ``database`` – nested dict with ``admin_password`` and ``db_name``
        """
        _, client = self._ensure_open()
        create_details = oci.database.models.CreateDatabaseBase(
            db_home_id=details.get("db_home_id"),
            source="NONE",
            database=oci.database.models.CreateDatabaseDetails(**details.get("database", {})),
        )
        response = await self._call(client.create_database, create_details)
        return DatabaseDetails.from_oci_response(response.data)

    async def update(self, resource_id: str, details: dict[str, Any]) -> DatabaseDetails:
        """Apply *details* to the database identified by *resource_id*.

        Accepted keys inside *details* mirror :class:`oci.database.models.UpdateDatabaseDetails`.
        """
        _, client = self._ensure_open()
        update_details = oci.database.models.UpdateDatabaseDetails(**details)
        response = await self._call(client.update_database, resource_id, update_details)
        return DatabaseDetails.from_oci_response(response.data)

    async def delete(self, resource_id: str) -> None:
        """Initiate deletion of the database identified by *resource_id*.

        The OCI API is asynchronous: the database moves to TERMINATING state
        and eventually reaches TERMINATED.  Callers that need to wait for
        completion should poll :meth:`get` or use an OCI waiter.
        """
        _, client = self._ensure_open()
        await self._call(client.delete_database, resource_id)
