# coding: utf-8
# Copyright (c) 2016, 2026, Oracle and/or its affiliates. All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at
# https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at
# http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DatabaseSummary:
    """Lightweight view of a Database resource returned by list operations."""

    id: str
    compartment_id: str
    display_name: str
    lifecycle_state: str
    db_name: str
    db_unique_name: str
    db_workload: str | None = None
    db_version: str | None = None
    time_created: str | None = None
    freeform_tags: dict[str, str] = field(default_factory=dict)
    defined_tags: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_oci_response(cls, data: Any) -> "DatabaseSummary":
        return cls(
            id=data.id,
            compartment_id=data.compartment_id,
            display_name=data.db_name,
            lifecycle_state=data.lifecycle_state,
            db_name=data.db_name,
            db_unique_name=data.db_unique_name,
            db_workload=getattr(data, "db_workload", None),
            db_version=getattr(data, "db_version", None),
            time_created=str(data.time_created) if getattr(data, "time_created", None) else None,
            freeform_tags=getattr(data, "freeform_tags", {}) or {},
            defined_tags=getattr(data, "defined_tags", {}) or {},
        )


@dataclass
class DatabaseDetails(DatabaseSummary):
    """Full details of a Database resource returned by get operations."""

    character_set: str | None = None
    ncharacter_set: str | None = None
    pdb_name: str | None = None
    db_backup_config: dict[str, Any] | None = None
    connection_strings: dict[str, Any] | None = None
    kms_key_id: str | None = None

    @classmethod
    def from_oci_response(cls, data: Any) -> "DatabaseDetails":  # type: ignore[override]
        base = DatabaseSummary.from_oci_response(data)
        return cls(
            **base.__dict__,
            character_set=getattr(data, "character_set", None),
            ncharacter_set=getattr(data, "ncharacter_set", None),
            pdb_name=getattr(data, "pdb_name", None),
            db_backup_config=_to_dict(getattr(data, "db_backup_config", None)),
            connection_strings=_to_dict(getattr(data, "connection_strings", None)),
            kms_key_id=getattr(data, "kms_key_id", None),
        )


def _to_dict(obj: Any) -> dict[str, Any] | None:
    if obj is None:
        return None
    return obj.__dict__ if hasattr(obj, "__dict__") else dict(obj)
