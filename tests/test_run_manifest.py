from __future__ import annotations

from pathlib import Path

from app.core.observability import run_manifest


def test_register_run_writes_manifest_and_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_manifest, "get_app_state_dir", lambda: tmp_path)

    run_dir = run_manifest.register_run(
        job_id="job-123",
        run_type="training",
        spec={"epochs": 10},
        artifacts={"project": "/tmp/runs"},
    )

    manifest = run_dir / "run_manifest.json"
    assert manifest.exists()
    assert run_manifest.get_run_folder("job-123") == run_dir
