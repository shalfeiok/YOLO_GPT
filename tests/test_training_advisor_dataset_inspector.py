from pathlib import Path

from PIL import Image

from app.core.training_advisor.dataset_inspector import DatasetInspector


def _make_dataset(root: Path) -> Path:
    (root / "images" / "train").mkdir(parents=True)
    (root / "labels" / "train").mkdir(parents=True)
    (root / "data.yaml").write_text("train: images/train\nval: images/train\nnames: [a,b]\n", encoding="utf-8")
    return root


def test_inspector_detects_empty_and_out_of_range(tmp_path: Path) -> None:
    ds = _make_dataset(tmp_path)
    img = ds / "images" / "train" / "a.jpg"
    Image.new("RGB", (100, 100), color="red").save(img)
    (ds / "labels" / "train" / "a.txt").write_text("0 1.2 0.5 0.2 0.2\n", encoding="utf-8")
    rep = DatasetInspector().inspect(ds)
    assert any("bbox out of range" in e for e in rep["errors"])


def test_inspector_detects_imbalance(tmp_path: Path) -> None:
    ds = _make_dataset(tmp_path)
    for i in range(7):
        img = ds / "images" / "train" / f"a{i}.jpg"
        Image.new("RGB", (64, 64), color="blue").save(img)
        cls = 0 if i < 6 else 1
        (ds / "labels" / "train" / f"a{i}.txt").write_text(f"{cls} 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    rep = DatasetInspector().inspect(ds)
    assert any("imbalance" in w for w in rep["warnings"])
