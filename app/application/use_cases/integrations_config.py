"""Use-cases for importing/exporting the full integrations configuration.

The Integrations UI edits many individual section configs (Comet, DVC, etc.).
These use-cases provide a simple *backup/restore* mechanism for the entire
integrations JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.features.integrations_config import (
    export_config_to_file,
    import_config_from_file,
    load_config,
    save_config,
)


class IntegrationsConfigRepository(Protocol):
    def load(self) -> dict[str, Any]:
        ...

    def save(self, cfg: dict[str, Any]) -> None:
        ...

    def export_to(self, cfg: dict[str, Any], export_path: Path) -> None:
        ...

    def import_from(self, import_path: Path) -> dict[str, Any]:
        ...


class DefaultIntegrationsConfigRepository(IntegrationsConfigRepository):
    """File-based repository using :mod:`app.features.integrations_config`."""

    def load(self) -> dict[str, Any]:
        return load_config()

    def save(self, cfg: dict[str, Any]) -> None:
        save_config(cfg)

    def export_to(self, cfg: dict[str, Any], export_path: Path) -> None:
        export_config_to_file(cfg, export_path)

    def import_from(self, import_path: Path) -> dict[str, Any]:
        return import_config_from_file(import_path)


@dataclass(frozen=True, slots=True)
class ExportIntegrationsConfigRequest:
    path: Path


@dataclass(frozen=True, slots=True)
class ImportIntegrationsConfigRequest:
    path: Path


class ExportIntegrationsConfigUseCase:
    def __init__(self, repo: IntegrationsConfigRepository) -> None:
        self._repo = repo

    def execute(self, req: ExportIntegrationsConfigRequest) -> None:
        cfg = self._repo.load()
        self._repo.export_to(cfg, req.path)


class ImportIntegrationsConfigUseCase:
    def __init__(self, repo: IntegrationsConfigRepository) -> None:
        self._repo = repo

    def execute(self, req: ImportIntegrationsConfigRequest) -> None:
        cfg = self._repo.import_from(req.path)
        self._repo.save(cfg)
