from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config import PROJECT_ROOT


def get_app_state_dir(app_folder_name: str = ".app_state") -> Path:
    """Return a writable directory for storing app state (jobs history, logs, etc).

    Preference order:
    1) <PROJECT_ROOT>/.app_state if writable (good for dev / tests)
    2) OS user data dir (~/.local/share/<app>, %APPDATA%\\<app>, etc)
    """
    # 1) Project-local state folder (dev-friendly)
    proj_dir = PROJECT_ROOT / app_folder_name
    try:
        proj_dir.mkdir(parents=True, exist_ok=True)
        test_file = proj_dir / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return proj_dir
    except Exception:
        import logging

        logging.getLogger(__name__).debug(
            "Project dir probe failed; falling back to user data dir", exc_info=True
        )
    # 2) User data dir
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return (base / "app_6_all_method").resolve()
    if sys.platform == "darwin":
        return (Path.home() / "Library" / "Application Support" / "app_6_all_method").resolve()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".local" / "share")
    return (base / "app_6_all_method").resolve()
