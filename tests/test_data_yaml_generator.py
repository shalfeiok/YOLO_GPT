from pathlib import Path

import yaml

from app.services.data_yaml_generator import generate_data_yaml


def _touch_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"img")


def test_sequences_and_multiple_test_splits(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    _touch_image(root / "train" / "sequences" / "001" / "img0001.jpg")
    _touch_image(root / "val" / "sequences" / "002" / "img0001.jpg")
    _touch_image(root / "test-dev" / "sequences" / "003" / "img0001.jpg")
    _touch_image(root / "test-challenge" / "sequences" / "004" / "img0001.jpg")
    (root / "classes.txt").write_text("cat\ndog\n", encoding="utf-8")

    result = generate_data_yaml(root)
    payload = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))

    assert payload["train"] == "train/sequences"
    assert payload["val"] == "val/sequences"
    assert payload["test"] == ["test-challenge/sequences", "test-dev/sequences"]
    assert result.names_source == "classes.txt"


def test_prefers_images_folder(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    _touch_image(root / "train" / "images" / "a.jpg")
    _touch_image(root / "val" / "images" / "b.jpg")
    (root / "names.txt").write_text("person\n", encoding="utf-8")

    generate_data_yaml(root)
    payload = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))

    assert payload["train"] == "train/images"
    assert payload["val"] == "val/images"


def test_list_files_split_detection(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    root.mkdir(parents=True)
    (root / "trainlist.txt").write_text("train/001.jpg\n", encoding="utf-8")
    (root / "vallist.txt").write_text("val/001.jpg\n", encoding="utf-8")
    (root / "testlist.txt").write_text("test/001.jpg\n", encoding="utf-8")
    (root / "obj.names").write_text("car\n", encoding="utf-8")

    generate_data_yaml(root)
    payload = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))

    assert payload["train"] == "trainlist.txt"
    assert payload["val"] == "vallist.txt"
    assert payload["test"] == "testlist.txt"


def test_missing_val_adds_warning(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    _touch_image(root / "train" / "sequences" / "001" / "img0001.jpg")

    result = generate_data_yaml(root)

    assert "split 'val' not found" in result.warnings


def test_initialization_only_split_is_skipped(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    _touch_image(root / "train" / "sequences" / "001" / "img0001.jpg")
    _touch_image(root / "val" / "sequences" / "001" / "img0001.jpg")
    (root / "test-challenge_initialization" / "initialization").mkdir(parents=True)
    (root / "names.txt").write_text("obj\n", encoding="utf-8")

    result = generate_data_yaml(root)
    payload = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))

    assert "test" not in payload
    assert "split contains no images, skipped: test-challenge_initialization" in result.warnings


def test_fallback_names_when_missing_sources(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    _touch_image(root / "train" / "sequences" / "001" / "img0001.jpg")
    _touch_image(root / "val" / "sequences" / "001" / "img0001.jpg")

    result = generate_data_yaml(root)
    payload = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))

    assert payload["names"] == ["class0"]
    assert result.names_source == "fallback_default"
    assert "names source not found: fallback to ['class0']" in result.warnings
