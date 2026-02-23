from pathlib import Path

import yaml

from app.services.data_yaml_generator import CreateDataYamlUseCase, DatasetTypeDetector


def _touch_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"img")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_detect_yolo_ready() -> None:
    # req #1
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
        root = Path(td)
        _touch_image(root / "train" / "images" / "1.jpg")
        _write(root / "train" / "labels" / "1.txt", "0 0.5 0.5 0.2 0.2\n")

        result = DatasetTypeDetector().detect(root)
        assert result.dataset_type == "YOLO_READY"


def test_detect_vid(tmp_path: Path) -> None:
    # req #2
    root = tmp_path / "vid"
    _touch_image(root / "train" / "sequences" / "uav0001" / "0000001.jpg")
    rows = "\n".join("1,1,10,10,20,20,1,0,0,0" for _ in range(25))
    _write(root / "train" / "annotations" / "uav0001.txt", rows)

    result = DatasetTypeDetector().detect(root)
    assert result.dataset_type == "VID"


def test_detect_sot(tmp_path: Path) -> None:
    # req #3
    root = tmp_path / "sot"
    _touch_image(root / "train" / "sequences" / "seq01" / "img0001.jpg")
    rows = "\n".join("10,20,30,40" for _ in range(30))
    _write(root / "train" / "annotations" / "seq01.txt", rows)

    result = DatasetTypeDetector().detect(root)
    assert result.dataset_type == "SOT"


def test_detect_cc(tmp_path: Path) -> None:
    # req #4
    root = tmp_path / "cc"
    _write(root / "train" / "annotations" / "count.txt", "1,25\n2,30\n3,31\n" * 10)

    result = DatasetTypeDetector().detect(root)
    assert result.dataset_type == "CC"


def test_detect_det(tmp_path: Path) -> None:
    # req #5
    root = tmp_path / "det"
    _touch_image(root / "train" / "images" / "000001.jpg")
    _write(root / "train" / "annotations" / "000001.txt", "10,10,20,20,1,3,0,0\n" * 12)

    result = DatasetTypeDetector().detect(root)
    assert result.dataset_type == "DET"


def test_layout_prefers_list_files(tmp_path: Path) -> None:
    # req #6
    root = tmp_path / "ds"
    root.mkdir(parents=True)
    _write(root / "trainlist.txt", "train/images/1.jpg\n")
    _write(root / "vallist.txt", "val/images/1.jpg\n")
    _write(root / "testlist.txt", "test/images/1.jpg\n")
    _write(root / "classes.txt", "a\n")

    result = CreateDataYamlUseCase().run(root)
    data = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))

    assert result.train == "trainlist.txt"
    assert data["test"] == "testlist.txt"


def test_layout_folder_splits_with_multiple_tests(tmp_path: Path) -> None:
    # req #7
    root = tmp_path / "vid"
    _touch_image(root / "train" / "sequences" / "a" / "1.jpg")
    _touch_image(root / "val" / "sequences" / "b" / "1.jpg")
    _touch_image(root / "test-dev" / "sequences" / "c" / "1.jpg")
    _touch_image(root / "test-challenge" / "sequences" / "d" / "1.jpg")
    _write(root / "train" / "annotations" / "a.txt", "1,1,10,10,20,20,1,0,0,0\n" * 22)

    result = CreateDataYamlUseCase().run(root)
    data = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))

    assert isinstance(data["test"], list)
    assert result.test == ["test-challenge/sequences", "test-dev/sequences"]


def test_initialization_only_split_skipped(tmp_path: Path) -> None:
    # req #8
    root = tmp_path / "vid"
    _touch_image(root / "train" / "sequences" / "a" / "1.jpg")
    _touch_image(root / "val" / "sequences" / "b" / "1.jpg")
    (root / "test-challenge_initialization" / "initialization").mkdir(parents=True)
    _write(root / "train" / "annotations" / "a.txt", "1,1,10,10,20,20,1,0,0,0\n" * 21)

    result = CreateDataYamlUseCase().run(root)
    assert any("initialization-only split skipped" in w for w in result.warnings)


def test_names_from_existing_yaml_not_overwritten(tmp_path: Path) -> None:
    # req #9
    root = tmp_path / "ready"
    _touch_image(root / "train" / "images" / "1.jpg")
    _touch_image(root / "val" / "images" / "1.jpg")
    _write(root / "train" / "labels" / "1.txt", "0 0.5 0.5 0.2 0.2\n")
    _write(root / "data.yaml", "names:\n  0: pedestrian\n  1: people\n")

    result = CreateDataYamlUseCase().run(root)
    assert result.names[0] == "pedestrian"
    assert result.names_source.startswith("data.yaml")


def test_names_from_classes_file(tmp_path: Path) -> None:
    # req #10
    root = tmp_path / "ds"
    _touch_image(root / "train" / "images" / "1.jpg")
    _touch_image(root / "val" / "images" / "1.jpg")
    _write(root / "train" / "annotations" / "1.txt", "10,10,20,20,1,3,0,0\n" * 15)
    _write(root / "classes.txt", "cat\ndog\n")

    result = CreateDataYamlUseCase().run(root)
    assert result.names == {0: "cat", 1: "dog"}


def test_visdrone_defaults_for_vid_without_names(tmp_path: Path) -> None:
    # req #11
    root = tmp_path / "vid"
    _touch_image(root / "train" / "sequences" / "a" / "1.jpg")
    _touch_image(root / "val" / "sequences" / "b" / "1.jpg")
    _write(root / "train" / "annotations" / "a.txt", "1,1,10,10,20,20,1,0,0,0\n" * 25)

    result = CreateDataYamlUseCase().run(root)
    assert result.names_source == "visdrone_defaults"
    assert result.names[0] == "pedestrian"
    assert result.names[9] == "motor"


def test_unknown_fallback_names(tmp_path: Path) -> None:
    # req #12
    root = tmp_path / "unknown"
    root.mkdir(parents=True)

    result = CreateDataYamlUseCase().run(root)
    assert result.detected_type == "UNKNOWN"
    assert result.names == {0: "class0"}
    assert any("placeholder names" in w for w in result.warnings)


def test_yaml_key_order_is_stable(tmp_path: Path) -> None:
    root = tmp_path / "vid"
    _touch_image(root / "train" / "sequences" / "a" / "1.jpg")
    _touch_image(root / "val" / "sequences" / "b" / "1.jpg")
    _touch_image(root / "test-dev" / "sequences" / "c" / "1.jpg")
    _write(root / "train" / "annotations" / "a.txt", "1,1,10,10,20,20,1,0,0,0\n" * 20)

    CreateDataYamlUseCase().run(root)
    lines = (root / "data.yaml").read_text(encoding="utf-8").splitlines()
    keys = [line.split(":", 1)[0] for line in lines if line and not line.startswith(" ") and ":" in line]
    assert keys[:6] == ["path", "train", "val", "test", "nc", "names"]


def test_normalizes_dataset_root_from_split_subfolder(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    _touch_image(root / "train" / "sequences" / "a" / "1.jpg")
    _touch_image(root / "val" / "sequences" / "b" / "1.jpg")
    _write(root / "train" / "annotations" / "a.txt", "1,1,10,10,20,20,1,0,0,0\n" * 20)

    result = CreateDataYamlUseCase().run(root / "train")
    assert result.data_yaml_path == root / "data.yaml"


def test_existing_data_yaml_creates_backup(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    _touch_image(root / "train" / "images" / "1.jpg")
    _touch_image(root / "val" / "images" / "1.jpg")
    _write(root / "train" / "labels" / "1.txt", "0 0.5 0.5 0.2 0.2\n")
    _write(root / "data.yaml", "path: .\ntrain: old/train\n")

    CreateDataYamlUseCase().run(root)
    assert (root / "data.yaml.bak").exists()
