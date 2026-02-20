"""Тесты сборки объединённого data.yaml (DatasetConfigBuilder)."""
from pathlib import Path

import pytest
import yaml

from app.services.dataset_service import DatasetConfigBuilder


class TestDatasetConfigBuilder:
    """build_multi: объединение датасетов в один data.yaml."""

    def _create_dataset(
        self,
        base: Path,
        nc: int = 2,
        names: list[str] | None = None,
        with_valid: bool = True,
    ) -> None:
        (base / "train" / "images").mkdir(parents=True)
        if with_valid:
            (base / "valid" / "images").mkdir(parents=True)
        data = {"nc": nc, "names": names or [f"class_{i}" for i in range(nc)]}
        (base / "data.yaml").write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

    def test_empty_paths_raises(self) -> None:
        builder = DatasetConfigBuilder()
        with pytest.raises(ValueError, match="хотя бы один"):
            builder.build_multi([], Path("/out/data.yaml"))

    def test_build_multi_single_dataset(self, tmp_path: Path) -> None:
        ds1 = tmp_path / "ds1"
        self._create_dataset(ds1, nc=2, names=["cat", "dog"])
        out = tmp_path / "combined" / "data.yaml"
        builder = DatasetConfigBuilder()
        result = builder.build_multi([ds1], out)
        assert result == out
        assert out.exists()
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert data["nc"] == 2
        assert data["names"] == ["cat", "dog"]
        assert "train" in data
        assert "val" in data

    def test_build_multi_two_datasets(self, tmp_path: Path) -> None:
        ds1 = tmp_path / "ds1"
        ds2 = tmp_path / "ds2"
        self._create_dataset(ds1, nc=1, names=["a"])
        self._create_dataset(ds2, nc=2, names=["b", "c"])
        out = tmp_path / "out" / "data.yaml"
        builder = DatasetConfigBuilder()
        builder.build_multi([ds1, ds2], out)
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert data["nc"] == 2
        assert len(data["names"]) == 2
        assert len(data["train"]) == 2
        assert len(data["val"]) == 2

    def test_no_train_dir_raises(self, tmp_path: Path) -> None:
        nodata = tmp_path / "nodata"
        nodata.mkdir()
        (nodata / "data.yaml").write_text("nc: 1\nnames: [x]", encoding="utf-8")
        out = tmp_path / "out" / "data.yaml"
        builder = DatasetConfigBuilder()
        with pytest.raises(FileNotFoundError, match="train"):
            builder.build_multi([nodata], out)
