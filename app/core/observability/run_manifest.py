from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.paths import get_app_state_dir


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_type: str
    timestamp: str
    job_id: str
    spec: dict[str, Any]
    env: dict[str, Any]
    git_commit: str | None
    artifacts: dict[str, Any]


def _safe_git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        return out or None
    except Exception:
        return None


def _python_env() -> dict[str, Any]:
    env: dict[str, Any] = {}
    try:
        import sys

        env["python"] = sys.version.split()[0]
    except Exception:
        pass
    try:
        import torch  # type: ignore

        env["torch"] = getattr(torch, "__version__", None)
        env["cuda"] = getattr(torch.version, "cuda", None)
        if torch.cuda.is_available():
            env["gpu"] = torch.cuda.get_device_name(0)
    except Exception:
        pass
    return env


def _runs_root() -> Path:
    root = get_app_state_dir() / "runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def register_run(
    job_id: str, run_type: str, spec: dict[str, Any], artifacts: dict[str, Any]
) -> Path:
    root = _runs_root()
    run_dir = root / job_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_type=run_type,
        timestamp=datetime.now(UTC).isoformat(),
        job_id=job_id,
        spec=spec,
        env=_python_env(),
        git_commit=_safe_git_commit(),
        artifacts=artifacts,
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    index_path = root / "index.json"
    index: dict[str, str] = {}
    if index_path.exists():
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                index = {str(k): str(v) for k, v in raw.items()}
        except Exception:
            index = {}
    index[job_id] = str(run_dir)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_dir


def get_run_folder(job_id: str | None) -> Path | None:
    if not job_id:
        return None
    index_path = _runs_root() / "index.json"
    if not index_path.exists():
        return None
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    p = raw.get(job_id)
    if not isinstance(p, str):
        return None
    folder = Path(p)
    return folder if folder.exists() else None
