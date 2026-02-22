"""Integrations config (JSON).

Public API intentionally stays **dict-based** for backward compatibility.

Internally we validate and normalize data through a typed dataclass schema
(``app.features.integrations_schema``). This gives us:

- stable defaults for every section
- light type coercion (e.g. "30" -> 30)
- safety against missing keys

No new third-party dependencies are introduced.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import INTEGRATIONS_CONFIG_PATH
from app.features.integrations_migrations import migrate
from app.features.integrations_schema import IntegrationsConfig


def default_config() -> dict[str, Any]:
    """Return default integrations config (all sections)."""
    return IntegrationsConfig().to_dict()


def _normalize(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize raw config dict using the typed schema."""
    if not isinstance(data, Mapping):
        return default_config()
    migrated = migrate(data)
    normalized = IntegrationsConfig.from_dict(migrated).to_dict()
    # Always persist latest schema version marker.
    normalized["schema_version"] = IntegrationsConfig().schema_version
    return normalized


def load_config(path: Path | None = None) -> dict[str, Any]:
    """
    Load integrations config from JSON file.
    Returns default config if file missing or invalid.
    """
    p = path or INTEGRATIONS_CONFIG_PATH
    if not p.exists():
        return default_config()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return _normalize(data)
    except (json.JSONDecodeError, OSError):
        return default_config()


def save_config(config: dict[str, Any], path: Path | None = None) -> None:
    """Save integrations config to JSON file."""
    p = path or INTEGRATIONS_CONFIG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(_normalize(config), f, indent=2, ensure_ascii=False)


def export_config_to_file(config: dict[str, Any], export_path: Path) -> None:
    """Export full config to a user-chosen path (e.g. backup)."""
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(_normalize(config), f, indent=2, ensure_ascii=False)


def import_config_from_file(import_path: Path) -> dict[str, Any]:
    """
    Import config from file; merge with defaults (so structure is valid).
    Returns merged config (caller may then save_config).
    """
    if not import_path.exists():
        return default_config()
    try:
        with open(import_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return default_config()
    return _normalize(data)
