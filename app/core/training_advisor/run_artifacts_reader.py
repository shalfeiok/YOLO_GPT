from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class RunArtifactsReader:
    def read(self, run_folder: Path | None) -> dict[str, Any]:
        if run_folder is None or not run_folder.exists():
            return {"found": False, "warnings": ["run folder not provided"], "metrics": {}, "args": {}}
        out: dict[str, Any] = {"found": True, "warnings": [], "metrics": {}, "args": {}, "files": []}
        results_csv = run_folder / "results.csv"
        if results_csv.exists():
            out["files"].append(str(results_csv))
            lines = [ln.strip() for ln in results_csv.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if len(lines) >= 2:
                headers = lines[0].split(",")
                last = lines[-1].split(",")
                out["metrics"] = {k: v for k, v in zip(headers, last)}
        else:
            out["warnings"].append("results.csv not found")
        for name in ("args.yaml", "opt.yaml"):
            path = run_folder / name
            if path.exists():
                out["files"].append(str(path))
                out["args"] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                break
        if not out["args"]:
            out["warnings"].append("args.yaml/opt.yaml not found")
        event_files = list(run_folder.rglob("events.out.tfevents*"))
        out["event_files"] = [str(x) for x in event_files]
        if not event_files:
            out["warnings"].append("tfevents not found")
        return out
