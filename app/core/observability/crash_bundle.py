from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path

from app.config import INTEGRATIONS_CONFIG_PATH
from app.core.paths import get_app_state_dir


def create_crash_bundle(
    output_zip: Path,
    *,
    state_dir: Path | None = None,
    include_rotated_job_events: bool = True,
) -> Path:
    """Create a support bundle (logs + jobs history + config snapshots).

    The bundle is safe to generate any time and should never crash the app.
    """
    sd = state_dir or get_app_state_dir()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    def add_file(z: zipfile.ZipFile, p: Path, arcname: str) -> None:
        try:
            if p.exists() and p.is_file():
                z.write(p, arcname=arcname)
        except Exception:
            return

    jobs_events = sd / "jobs_events.jsonl"
    logs_dir = sd / "logs"
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Jobs events
        add_file(z, jobs_events, "state/jobs_events.jsonl")
        if include_rotated_job_events:
            for p in sorted(sd.glob("jobs_events.*.jsonl")):
                add_file(z, p, f"state/{p.name}")

        # Logs
        if logs_dir.exists():
            for p in sorted(logs_dir.glob("app.log*")):
                add_file(z, p, f"logs/{p.name}")

        # Config snapshots
        add_file(z, INTEGRATIONS_CONFIG_PATH, "config/integrations_config.json")

        # Minimal metadata
        meta = f"created_utc: {stamp}\nstate_dir: {sd}\n"
        try:
            z.writestr("meta.txt", meta)
        except Exception:
            import logging

            logging.getLogger(__name__).debug("Failed to write crash bundle meta", exc_info=True)
    return output_zip
