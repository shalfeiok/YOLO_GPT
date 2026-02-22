"""
SageMaker: clone template repo, cdk deploy (async), cleanup endpoint.

Ref: https://docs.ultralytics.com/ru/integrations/amazon-sagemaker/
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from app.config import PROJECT_ROOT

SAGEMAKER_TEMPLATE_REPO = "https://github.com/aws-samples/host-yolov8-on-sagemaker-endpoint.git"
TEMPLATE_DIR_NAME = "host-yolov8-on-sagemaker-endpoint"


def clone_sagemaker_template(target_dir: Path | None = None) -> tuple[bool, str]:
    """
    Clone host-yolov8-on-sagemaker-endpoint into project folder.
    Returns (success, path or error message).
    """
    base = target_dir or PROJECT_ROOT
    dest = base / TEMPLATE_DIR_NAME
    if dest.exists():
        return True, str(dest)
    try:
        r = subprocess.run(
            ["git", "clone", SAGEMAKER_TEMPLATE_REPO, str(dest)],
            cwd=base,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode == 0:
            return True, str(dest)
        return False, r.stderr or r.stdout or "Ошибка git clone"
    except FileNotFoundError:
        return False, "Git не найден."
    except subprocess.TimeoutExpired:
        return False, "Таймаут клонирования."


def run_cdk_deploy(
    template_path: Path,
    on_output: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Run cdk deploy in template_path/yolov8-pytorch-cdk (or similar).
    Returns (success, message).
    """
    cdk_dir = template_path / "yolov8-pytorch-cdk"
    if not cdk_dir.is_dir():
        # try root
        cdk_dir = template_path
    if not (cdk_dir / "cdk.json").exists() and (template_path / "cdk.json").exists():
        cdk_dir = template_path
    try:
        r = subprocess.run(
            ["cdk", "deploy", "--require-approval", "never"],
            cwd=cdk_dir,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if on_output:
            if r.stdout:
                on_output(r.stdout)
            if r.stderr:
                on_output(r.stderr)
        if r.returncode == 0:
            return True, "CDK deploy завершён."
        return False, r.stderr or r.stdout or "Ошибка cdk deploy"
    except FileNotFoundError:
        return False, "CDK не найден. Установите: npm install -g aws-cdk"
    except subprocess.TimeoutExpired:
        return False, "Таймаут cdk deploy."
