"""Model export use case (application layer)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.features.model_export.domain import ModelExportConfig
from app.features.model_export.service import run_export


class ModelExporterPort(Protocol):
    """Port the application layer needs for model export."""

    def export(self, config: ModelExportConfig) -> Path | None:
        ...


class DefaultModelExporter:
    """Adapter over the feature-level export service."""

    def export(self, config: ModelExportConfig) -> Path | None:
        return run_export(config)


class ExportModelUseCase:
    """Export a trained model into another format."""

    def __init__(self, exporter: ModelExporterPort) -> None:
        self._exporter = exporter

    def execute(self, config: ModelExportConfig) -> Path | None:
        return self._exporter.export(config)
