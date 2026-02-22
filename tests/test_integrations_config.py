"""Тесты загрузки/сохранения конфига интеграций."""

import json
from pathlib import Path

from app.features.integrations_config import (
    default_config,
    export_config_to_file,
    import_config_from_file,
    load_config,
    save_config,
)


class TestDefaultConfig:
    """Структура конфига по умолчанию."""

    def test_has_all_sections(self) -> None:
        cfg = default_config()
        assert "albumentations" in cfg
        assert "comet" in cfg
        assert "dvc" in cfg
        assert "sagemaker" in cfg

    def test_albumentations_defaults(self) -> None:
        cfg = default_config()
        a = cfg["albumentations"]
        assert a["enabled"] is False
        assert a["use_standard"] is True
        assert a["custom_transforms"] == []
        assert a["transform_p"] == 0.5

    def test_comet_defaults(self) -> None:
        cfg = default_config()
        c = cfg["comet"]
        assert c["project_name"] == "yolo26-project"
        assert c["mode"] == "online"

    def test_has_guides_sections(self) -> None:
        cfg = default_config()
        assert "seg_isolation" in cfg
        assert "model_validation" in cfg
        assert "ultralytics_solutions" in cfg
        assert cfg["seg_isolation"]["background"] == "black"
        assert cfg["model_validation"]["data_yaml"] == ""
        assert cfg["ultralytics_solutions"]["solution_type"] == "ObjectCounter"


class TestLoadSaveConfig:
    """Загрузка и сохранение в файл (с временным путём)."""

    def test_load_missing_returns_default(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        cfg = load_config(path=path)
        assert cfg == default_config()

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        original = default_config()
        original["comet"]["project_name"] = "my-project"
        save_config(original, path=path)
        loaded = load_config(path=path)
        assert loaded["comet"]["project_name"] == "my-project"
        assert loaded["albumentations"]["enabled"] is False

    def test_load_invalid_json_returns_default(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json {", encoding="utf-8")
        cfg = load_config(path=path)
        assert cfg == default_config()


class TestExportImport:
    """Экспорт и импорт конфигурации."""

    def test_export_creates_file(self, tmp_path: Path) -> None:
        export_path = tmp_path / "exported.json"
        cfg = default_config()
        export_config_to_file(cfg, export_path)
        assert export_path.exists()
        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data["albumentations"]["transform_p"] == 0.5

    def test_import_missing_returns_default(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.json"
        cfg = import_config_from_file(path)
        assert cfg == default_config()

    def test_import_merge_with_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "partial.json"
        path.write_text('{"comet": {"project_name": "x"}}', encoding="utf-8")
        cfg = import_config_from_file(path)
        assert cfg["comet"]["project_name"] == "x"
        assert "albumentations" in cfg
        assert cfg["albumentations"]["transform_p"] == 0.5
