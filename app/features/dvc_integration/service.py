"""
DVC/DVCLive: check git/dvc init, run dvc init, run dvc plots diff (async).

Ref: https://docs.ultralytics.com/ru/integrations/dvc/
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from app.config import PROJECT_ROOT


def is_git_repo(path: Path | None = None) -> bool:
    p = path or PROJECT_ROOT
    return (p / ".git").is_dir()


def is_dvc_initialized(path: Path | None = None) -> bool:
    p = path or PROJECT_ROOT
    return (p / ".dvc").is_dir()


def get_current_branch(path: Path | None = None) -> str:
    p = path or PROJECT_ROOT
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=p,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout:
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def init_dvc_in_project(path: Path | None = None) -> tuple[bool, str]:
    """
    Run `dvc init` in project. Returns (success, message).
    """
    p = path or PROJECT_ROOT
    if not is_git_repo(p):
        return False, "Сначала инициализируйте Git: git init"
    try:
        r = subprocess.run(
            ["dvc", "init"],
            cwd=p,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            return True, "DVC инициализирован."
        return False, r.stderr or r.stdout or "Ошибка dvc init"
    except FileNotFoundError:
        return False, "Команда dvc не найдена. Установите: pip install dvclive dvc"
    except subprocess.TimeoutExpired:
        return False, "Таймаут dvc init"


def run_dvc_plots_diff(
    project_path: Path | None = None,
    on_output: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Run `dvc plots diff $(dvc exp list --names-only)` to generate HTML.
    Returns (success, path_to_html or error message).
    """
    p = project_path or PROJECT_ROOT
    if not is_dvc_initialized(p):
        return False, "DVC не инициализирован. Нажмите «Инициализировать DVC в проекте»."
    try:
        list_cmd = subprocess.run(
            ["dvc", "exp", "list", "--names-only"],
            cwd=p,
            capture_output=True,
            text=True,
            timeout=10,
        )
        names = (list_cmd.stdout or "").strip().splitlines() if list_cmd.returncode == 0 else []
        if not names:
            return False, "Нет экспериментов (dvc exp list пуст). Запустите обучение с включённым DVC."
        cmd = ["dvc", "plots", "diff"] + names
        if on_output:
            on_output(" ".join(cmd) + "\n")
        r = subprocess.run(cmd, cwd=p, capture_output=True, text=True, timeout=60)
        if on_output:
            if r.stdout:
                on_output(r.stdout)
            if r.stderr:
                on_output(r.stderr)
        if r.returncode == 0:
            html = p / "dvc_plots" / "index.html"
            if html.exists():
                return True, str(html)
            return True, str(p / "dvc_plots")
        return False, r.stderr or r.stdout or "Ошибка dvc plots diff"
    except FileNotFoundError:
        return False, "Команда dvc не найдена."
    except subprocess.TimeoutExpired:
        return False, "Таймаут."
