from __future__ import annotations

from app.ui.infrastructure.file_dialogs import get_open_json_path, get_save_json_path


class IntegrationsConfigActionsMixin:
    def _export_config(self) -> None:
        path = get_save_json_path(self, title="Экспорт конфигурации")
        if not path:
            return
        try:
            self._vm.export_integrations_config(path)
            self._toast_ok("Экспорт", f"Конфигурация сохранена: {path}")
        except Exception as e:
            self._toast_err("Ошибка", str(e))

    def _import_config(self) -> None:
        path = get_open_json_path(self, title="Импорт конфигурации")
        if not path:
            return
        try:
            self._vm.import_integrations_config(path)
            self._toast_ok("Импорт", "Конфигурация загружена и сохранена в приложение.")
        except Exception as e:
            self._toast_err("Ошибка", str(e))
