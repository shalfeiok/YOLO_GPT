"""
Entry point for Qt-based YOLO Desktop Studio UI.

Run: python main.py
Requires: pip install -r requirements.txt -r requirements-dev.txt

Phase 1: opens main window with geometry persistence. No training/detection UI yet.
"""
from __future__ import annotations

import sys
import warnings

from app.core.observability.logging_config import setup_logging
from app.ui.infrastructure import (
    AppSettings,
    Container,
    NotificationCenter,
    TrainingSignals,
    create_application,
    install_error_boundary,
)
from app.ui.infrastructure.application import run_application
from app.ui.shell import MainWindow


def main() -> None:
    # PyTorch CUDA использует устаревший pynvml; предупреждение не исправить из приложения
    warnings.filterwarnings("ignore", category=FutureWarning, module="torch.cuda")
    setup_logging()
    app = create_application()
    settings = AppSettings()
    from app.ui.theme.manager import ThemeManager
    theme_manager = ThemeManager(settings)
    theme_manager.set_theme(settings.get_theme())

    container = Container()
    # Ensure job tracking is attached before any UI action can submit background work.
    # Without this eager init, jobs started before opening the Jobs tab are not tracked.
    _ = container.job_registry
    container.theme_manager = theme_manager
    training_signals = TrainingSignals()

    window = MainWindow(settings, container=container, signals=training_signals)
    window.show()

    notifications = NotificationCenter(window)
    container.notifications = notifications
    install_error_boundary(notifications)

    run_application(app)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
