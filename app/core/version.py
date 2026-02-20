"""Build/version metadata.

This project is usually run from source (python main.py) and can also be packaged.
When packaged, git metadata is typically not available, so we rely on environment
variables injected at build time.
"""

from __future__ import annotations

import os


def get_build_info() -> dict[str, str]:
    """Return build metadata.

    Environment variables (set by CI/build scripts):
    - YDS_VERSION: human readable version (e.g. "1.2.0" or "0.0.0-dev")
    - YDS_GIT_SHA: short git sha
    - YDS_BUILD_DATE: ISO date (YYYY-MM-DD) or datetime
    """

    version = os.getenv("YDS_VERSION", "0.0.0-dev")
    sha = os.getenv("YDS_GIT_SHA", "dev")
    build_date = os.getenv("YDS_BUILD_DATE", "")
    return {"version": version, "git_sha": sha, "build_date": build_date}


def get_version_string() -> str:
    info = get_build_info()
    ver = info["version"].strip() or "0.0.0-dev"
    sha = info["git_sha"].strip() or "dev"
    date = info["build_date"].strip()
    if date:
        return f"v{ver} ({sha}, {date})"
    return f"v{ver} ({sha})"
