"""Тесты доменных моделей гайдов: сегментация, валидация, Solutions."""


from app.features.model_validation.domain import ModelValidationConfig
from app.features.segmentation_isolation.domain import SegIsolationConfig
from app.features.ultralytics_solutions.domain import (
    SOLUTION_TYPES,
    SolutionsConfig,
)


class TestModelValidationConfig:
    """ModelValidationConfig from_dict / to_dict."""

    def test_from_dict_empty(self) -> None:
        cfg = ModelValidationConfig.from_dict(None)
        assert cfg.data_yaml == ""
        assert cfg.weights_path == ""

    def test_from_dict_partial(self) -> None:
        cfg = ModelValidationConfig.from_dict({"data_yaml": "coco8.yaml"})
        assert cfg.data_yaml == "coco8.yaml"
        assert cfg.weights_path == ""

    def test_to_dict_roundtrip(self) -> None:
        cfg = ModelValidationConfig(data_yaml="data.yaml", weights_path="best.pt")
        d = cfg.to_dict()
        restored = ModelValidationConfig.from_dict(d)
        assert restored.data_yaml == cfg.data_yaml
        assert restored.weights_path == cfg.weights_path


class TestSegIsolationConfig:
    """SegIsolationConfig from_dict / to_dict."""

    def test_from_dict_defaults(self) -> None:
        cfg = SegIsolationConfig.from_dict({})
        assert cfg.background == "black"
        assert cfg.crop is True

    def test_from_dict_transparent(self) -> None:
        cfg = SegIsolationConfig.from_dict({"background": "transparent", "crop": False})
        assert cfg.background == "transparent"
        assert cfg.crop is False

    def test_to_dict_roundtrip(self) -> None:
        cfg = SegIsolationConfig(
            model_path="yolo11n-seg.pt",
            source_path="/img",
            output_dir="/out",
            background="transparent",
            crop=False,
        )
        d = cfg.to_dict()
        restored = SegIsolationConfig.from_dict(d)
        assert restored.model_path == cfg.model_path
        assert restored.background == cfg.background
        assert restored.crop == cfg.crop


class TestSolutionsConfig:
    """SolutionsConfig from_dict / to_dict."""

    def test_from_dict_defaults(self) -> None:
        cfg = SolutionsConfig.from_dict(None)
        assert cfg.solution_type == "ObjectCounter"
        assert cfg.region_points == "[(20, 400), (1260, 400)]"
        assert cfg.fps == 30.0
        assert cfg.colormap == "COLORMAP_JET"

    def test_from_dict_heatmap(self) -> None:
        cfg = SolutionsConfig.from_dict({"solution_type": "Heatmap", "colormap": "COLORMAP_PARULA"})
        assert cfg.solution_type == "Heatmap"
        assert cfg.colormap == "COLORMAP_PARULA"

    def test_to_dict_roundtrip(self) -> None:
        cfg = SolutionsConfig(
            solution_type="TrackZone",
            model_path="yolo26n.pt",
            source="0",
            output_path="out.avi",
            region_points="[(0,0),(100,100)]",
            fps=25.0,
            colormap="COLORMAP_INFERNO",
        )
        d = cfg.to_dict()
        restored = SolutionsConfig.from_dict(d)
        assert restored.solution_type == cfg.solution_type
        assert restored.fps == cfg.fps
        assert restored.colormap == cfg.colormap


class TestSolutionTypes:
    """Константа SOLUTION_TYPES."""

    def test_contains_expected(self) -> None:
        assert "DistanceCalculation" in SOLUTION_TYPES
        assert "Heatmap" in SOLUTION_TYPES
        assert "ObjectCounter" in SOLUTION_TYPES
        assert "RegionCounter" in SOLUTION_TYPES
        assert "SpeedEstimator" in SOLUTION_TYPES
        assert "TrackZone" in SOLUTION_TYPES
        assert len(SOLUTION_TYPES) == 6
