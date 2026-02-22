"""Versioned migrations for integrations_config.

The app historically stored integrations settings as an unversioned JSON
dict. To evolve the config safely over time, we keep a small migration
layer that upgrades older configs to the latest schema version.

Design goals:
- Backward compatible: old configs load without errors
- Forward tolerant: unknown keys are preserved (and ignored by schema)
- No third-party dependencies
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

LATEST_SCHEMA_VERSION = 2


def _as_int(value: Any, default: int) -> int:
    try:
        if isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def migrate(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a migrated copy of *raw*.

    If *raw* is not a mapping, returns an empty dict (schema will fill
    defaults).
    """
    if not isinstance(raw, Mapping):
        return {}

    data: dict[str, Any] = dict(raw)  # shallow copy
    version = _as_int(data.get("schema_version"), 0)

    # Step-by-step migrations (so future versions can stack cleanly).
    while version < LATEST_SCHEMA_VERSION:
        if version == 0:
            data = _migrate_v0_to_v1(data)
            version = 1
        elif version == 1:
            data = _migrate_v1_to_v2(data)
            version = 2
        else:
            # Unknown old version; fall back to latest marker.
            break

    data["schema_version"] = LATEST_SCHEMA_VERSION
    return data


def _migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Initial migration: introduce schema_version and normalize legacy keys."""
    out = dict(data)

    # Legacy section name normalization (keep both to be safe).
    if "segmentation_isolation" in out and "seg_isolation" not in out:
        out["seg_isolation"] = out.get("segmentation_isolation")

    # Another plausible legacy name.
    if "ultralytics" in out and "ultralytics_solutions" not in out:
        out["ultralytics_solutions"] = out.get("ultralytics")

    return out


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Add default jobs policy section."""
    out = dict(data)
    if "jobs" not in out:
        out["jobs"] = {}
    return out
