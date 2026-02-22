"""Central logging configuration.

Keep it lightweight: stdlib logging only.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.paths import get_app_state_dir


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),  # noqa: UP017 (py310 compat)
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Include selected extras if present
        for key in ("event", "model", "project", "epoch", "fraction"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    *,
    level: str | int | None = None,
    json_logs: bool | None = None,
    log_to_file: bool | None = None,
    state_dir: Path | None = None,
) -> None:
    """Configure root logging.

    - level: "INFO"/"DEBUG" or logging level int. Defaults to env LOG_LEVEL or INFO.
    - json_logs: bool. Defaults to env LOG_JSON ("1"/"true").
    """

    env_level = os.getenv("LOG_LEVEL", "INFO")
    lvl = level if level is not None else env_level
    if isinstance(lvl, str):
        lvl = getattr(logging, lvl.upper(), logging.INFO)

    if json_logs is None:
        json_logs = os.getenv("LOG_JSON", "0").lower() in {"1", "true", "yes"}

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    if json_logs:
        stream_handler.setFormatter(_JsonFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    if log_to_file is None:
        log_to_file = os.getenv("LOG_FILE", "1").lower() in {"1", "true", "yes"}
    file_handler: logging.Handler | None = None
    if log_to_file:
        try:
            sd = state_dir or get_app_state_dir()
            logs_dir = sd / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = logs_dir / "app.log"
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            # File logs should be plain text for easier sharing.
            file_handler.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
        except Exception:
            file_handler = None

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(stream_handler)
    if file_handler is not None:
        root.addHandler(file_handler)
    root.setLevel(int(lvl))

    # Reduce noise from verbose libs.
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
