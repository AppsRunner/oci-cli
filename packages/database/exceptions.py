# coding: utf-8
# Copyright (c) 2016, 2026, Oracle and/or its affiliates. All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at
# https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at
# http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import annotations


class RepositoryError(Exception):
    """Base exception for all repository errors."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ResourceNotFoundError(RepositoryError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource_id: str, resource_type: str = "resource") -> None:
        super().__init__(f"{resource_type} '{resource_id}' not found")
        self.resource_id = resource_id
        self.resource_type = resource_type


class ResourceConflictError(RepositoryError):
    """Raised when a create/update conflicts with existing state."""


class RepositoryOperationError(RepositoryError):
    """Raised when an OCI API call fails for an unexpected reason."""
