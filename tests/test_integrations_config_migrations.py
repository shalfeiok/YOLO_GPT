from __future__ import annotations

from pathlib import Path

from app.features.integrations_config import import_config_from_file
from app.features.integrations_migrations import LATEST_SCHEMA_VERSION, migrate


def test_migrate_v0_adds_schema_version_and_normalizes_keys() -> None:
    raw = {
        # no schema_version (v0)
        "segmentation_isolation": {"enabled": True},
        "ultralytics": {"enabled": False},
        "unknown_future_key": {"keep": "me"},
    }
    out = migrate(raw)

    assert out["schema_version"] == LATEST_SCHEMA_VERSION
    # Normalized aliases should be present for backward compatibility.
    assert "seg_isolation" in out
    assert "ultralytics_solutions" in out
    # Unknown keys should be preserved.
    assert out["unknown_future_key"] == {"keep": "me"}


def test_import_config_from_file_migrates_and_normalizes(tmp_path: Path) -> None:
    # Simulate a legacy config file.
    p = tmp_path / "integrations_config.json"
    p.write_text(
        '{"segmentation_isolation": {"enabled": true}, "ultralytics": {"enabled": false}}',
        encoding="utf-8",
    )

    cfg = import_config_from_file(p)
    # Import returns normalized dict with current schema marker.
    assert cfg["schema_version"] == LATEST_SCHEMA_VERSION
    assert "seg_isolation" in cfg
    assert "ultralytics_solutions" in cfg
