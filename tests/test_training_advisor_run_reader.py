from pathlib import Path

from app.core.training_advisor.run_artifacts_reader import RunArtifactsReader


def test_run_artifacts_reader_parses_metrics_and_args(tmp_path: Path) -> None:
    (tmp_path / "results.csv").write_text(
        "epoch,metrics/mAP50(B),train/box_loss\n1,0.25,0.4\n",
        encoding="utf-8",
    )
    (tmp_path / "args.yaml").write_text("imgsz: 640\nbatch: 16\n", encoding="utf-8")
    rep = RunArtifactsReader().read(tmp_path)
    assert rep["found"] is True
    assert rep["metrics"]["metrics/mAP50(B)"] == "0.25"
    assert rep["args"]["imgsz"] == 640


def test_run_artifacts_reader_handles_missing_folder(tmp_path: Path) -> None:
    rep = RunArtifactsReader().read(tmp_path / "missing")
    assert rep["found"] is False
