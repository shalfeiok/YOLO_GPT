"""
Базовый интерфейс бэкенда визуализации: отрисовка кадров в окне детекции.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from queue import Queue
from typing import Any


class IVisualizationBackend(ABC):
    """Интерфейс бэкенда отрисовки превью детекции."""

    @abstractmethod
    def get_id(self) -> str:
        """Идентификатор бэкенда (opencv, d3dshot_pytorch)."""
        ...

    @abstractmethod
    def get_display_name(self) -> str:
        """Название для UI."""
        ...

    def get_default_settings(self) -> dict[str, Any]:
        """Настройки по умолчанию для этого бэкенда."""
        return {}

    def get_settings_schema(self) -> list[dict[str, Any]]:
        """
        Схема полей настроек для построения UI динамически.
        Каждый элемент: {"key": str, "type": "int"|"bool"|"choice", "label": str, "default": Any,
                         "choices": list (для choice), "min"/"max" (для int)}.
        """
        return []

    def get_settings(self) -> dict[str, Any]:
        """Текущие настройки (из загруженного конфига или дефолт)."""
        return self.get_default_settings().copy()

    def apply_settings(self, settings: dict[str, Any]) -> None:
        """Применить настройки (сохраняются в инстансе)."""

    def supports_d3dshot_capture(self) -> bool:
        """True если бэкенд может захватывать «Весь экран» через D3DShot."""
        return False

    def capture_frame_fullscreen(self) -> Any:
        """Захват всего экрана (только при supports_d3dshot_capture()). Возвращает BGR numpy или None."""
        return None

    @abstractmethod
    def start_display(
        self,
        run_id: int,
        window_name: str,
        preview_queue: Queue,
        max_w: int,
        max_h: int,
        is_running_getter: Callable[[], bool],
        run_id_getter: Callable[[], int],
        on_stop: Callable[[], None] | None = None,
        on_q_key: Callable[[], None] | None = None,
        on_render_metrics: Callable[[float], None] | None = None,
    ) -> None:
        """
        Запустить поток отображения: читает кадры из preview_queue, ресайз/отрисовка, imshow.
        is_running_getter() и run_id_getter() — для проверки выхода.
        on_stop — по завершении потока, on_q_key — при нажатии Q.
        on_render_metrics(ms) — опционально: время отрисовки кадра в мс (для профилирования).
        """
        ...

    @abstractmethod
    def stop_display(self) -> None:
        """Остановить поток отображения и закрыть окно."""
        ...
