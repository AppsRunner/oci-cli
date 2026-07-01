# coding: utf-8
# Copyright (c) 2016, 2026, Oracle and/or its affiliates. All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at
# https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at
# http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

"""Abstract repository interface for database resources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")
S = TypeVar("S")


class Repository(ABC, Generic[T, S]):
    """Generic async repository interface.

    Type parameters:
        T: full detail type returned by get / create / update
        S: summary type returned by list
    """

    @abstractmethod
    async def get(self, resource_id: str) -> T:
        """Return the resource with *resource_id* or raise ResourceNotFoundError."""

    @abstractmethod
    async def list(self, compartment_id: str, **filters: Any) -> list[S]:
        """Return all resources in *compartment_id* matching the optional *filters*."""

    @abstractmethod
    async def create(self, compartment_id: str, details: dict[str, Any]) -> T:
        """Provision a new resource in *compartment_id* and return the created entity."""

    @abstractmethod
    async def update(self, resource_id: str, details: dict[str, Any]) -> T:
        """Apply *details* to the resource identified by *resource_id*."""

    @abstractmethod
    async def delete(self, resource_id: str) -> None:
        """Remove the resource identified by *resource_id*."""
