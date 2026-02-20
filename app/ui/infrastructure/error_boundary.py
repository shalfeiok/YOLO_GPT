from __future__ import annotations

import logging
import sys
import threading
import traceback


def install_error_boundary(notifications) -> None:
    """Install global exception hooks.

    This prevents silent crashes in background threads and gives users a hint where
    to find logs / crash bundle.
    """

    log = logging.getLogger(__name__)

    def _handle(exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        try:
            msg = "".join(traceback.format_exception(exc_type, exc, tb))
            log.error("Unhandled exception\n%s", msg)
            if notifications is not None:
                notifications.error("Произошла непредвиденная ошибка. Проверьте логи и crash bundle в разделе 'Задачи'.")
        finally:
            # Keep default behavior in console
            try:
                sys.__excepthook__(exc_type, exc, tb)
            except Exception:
                return

    sys.excepthook = _handle

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        _handle(args.exc_type, args.exc_value, args.exc_traceback)

    try:
        threading.excepthook = _thread_hook  # type: ignore[assignment]
    except Exception:
        return
