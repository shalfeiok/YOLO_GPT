"""Typed schema + light validation for integrations_config.
    @property
    def k(self) -> int:
        return int(self.k_folds)

    @k.setter
    def k(self, value: int) -> None:
        self.k_folds = int(value)


The config is stored as JSON and historically treated as a loose
``dict[str, Any]`` across the codebase.

To make the app more robust (and keep tests/headless runs stable), we
normalize that dict through dataclass models:

- missing keys are filled with defaults
- basic type coercion is applied (e.g. "30" -> 30)
- unknown keys are ignored (forward compatibility)

No third-party dependencies are required.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y", "on"}:
            return True
        if v in {"false", "0", "no", "n", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _as_int(value: Any, default: int) -> int:
    try:
        if isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        if isinstance(value, bool):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return str(value)
    return default


def _as_list(value: Any, default: list[Any]) -> list[Any]:
    if isinstance(value, list):
        return value
    return list(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


@dataclass(slots=True)
class AlbumentationsConfig:
    enabled: bool = False
    use_standard: bool = True
    custom_transforms: list[Any] = field(default_factory=list)
    transform_p: float = 0.5

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AlbumentationsConfig:
        m = _mapping(data)
        p = _clamp(_as_float(m.get("transform_p"), 0.5), 0.0, 1.0)
        return cls(
            enabled=_as_bool(m.get("enabled"), False),
            use_standard=_as_bool(m.get("use_standard"), True),
            custom_transforms=_as_list(m.get("custom_transforms"), []),
            transform_p=p,
        )


@dataclass(slots=True)
class CometConfig:
    enabled: bool = False
    api_key: str = ""
    project_name: str = "yolo26-project"
    max_image_predictions: int = 100
    eval_batch_logging_interval: int = 1
    eval_log_confusion_matrix: bool = True
    mode: str = "online"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CometConfig:
        m = _mapping(data)
        return cls(
            enabled=_as_bool(m.get("enabled"), False),
            api_key=_as_str(m.get("api_key"), ""),
            project_name=_as_str(m.get("project_name"), "yolo26-project"),
            max_image_predictions=_as_int(m.get("max_image_predictions"), 100),
            eval_batch_logging_interval=_as_int(m.get("eval_batch_logging_interval"), 1),
            eval_log_confusion_matrix=_as_bool(m.get("eval_log_confusion_matrix"), True),
            mode=_as_str(m.get("mode"), "online"),
        )


@dataclass(slots=True)
class DvcConfig:
    enabled: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DvcConfig:
        m = _mapping(data)
        return cls(enabled=_as_bool(m.get("enabled"), False))


@dataclass(slots=True)
class SagemakerConfig:
    instance_type: str = "ml.m5.4xlarge"
    endpoint_name: str = ""
    model_path: str = ""
    template_cloned_path: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SagemakerConfig:
        m = _mapping(data)
        return cls(
            instance_type=_as_str(m.get("instance_type"), "ml.m5.4xlarge"),
            endpoint_name=_as_str(m.get("endpoint_name"), ""),
            model_path=_as_str(m.get("model_path"), ""),
            template_cloned_path=_as_str(m.get("template_cloned_path"), ""),
        )


@dataclass(slots=True)
class JobsPolicyConfig:
    """Default retry/timeout policy for background jobs.

    Stored under top-level key "jobs" in integrations_config.
    Values are applied as defaults; specific actions may override them.
    """

    default_timeout_sec: int = 900
    retries: int = 0
    retry_backoff_sec: float = 1.0
    retry_jitter: float = 0.3
    retry_deadline_sec: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> JobsPolicyConfig:
        m = _mapping(data)
        return cls(
            default_timeout_sec=max(0, _as_int(m.get("default_timeout_sec"), 900)),
            retries=max(0, _as_int(m.get("retries"), 0)),
            retry_backoff_sec=max(0.0, _as_float(m.get("retry_backoff_sec"), 1.0)),
            retry_jitter=_clamp(_as_float(m.get("retry_jitter"), 0.3), 0.0, 1.0),
            retry_deadline_sec=max(0, _as_int(m.get("retry_deadline_sec"), 0)),
        )


@dataclass(slots=True)
class KFoldConfig:
    enabled: bool = False
    dataset_path: str = ""
    data_yaml_path: str = ""
    k_folds: int = 5
    random_state: int = 20
    output_path: str = ""
    weights_path: str = ""
    train_epochs: int = 100
    train_batch: int = 16
    train_project: str = "kfold_demo"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> KFoldConfig:
        m = _mapping(data)
        return cls(
            enabled=bool(m.get("enabled", False)),
            dataset_path=_as_str(m.get("dataset_path"), ""),
            data_yaml_path=_as_str(m.get("data_yaml_path"), ""),
            k_folds=max(2, _as_int(m.get("k_folds"), 5)),
            random_state=_as_int(m.get("random_state"), 20),
            output_path=_as_str(m.get("output_path"), ""),
            weights_path=_as_str(m.get("weights_path"), ""),
            train_epochs=max(1, _as_int(m.get("train_epochs"), 100)),
            train_batch=max(1, _as_int(m.get("train_batch"), 16)),
            train_project=_as_str(m.get("train_project"), "kfold_demo"),
        )


@dataclass(slots=True)
class TuningConfig:
    enabled: bool = False
    data_yaml: str = ""
    model_path: str = ""
    epochs: int = 30
    iterations: int = 300
    project: str = "runs/detect"
    name: str = "tune"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TuningConfig:
        m = _mapping(data)
        return cls(
            data_yaml=_as_str(m.get("data_yaml"), ""),
            model_path=_as_str(m.get("model_path"), ""),
            epochs=max(1, _as_int(m.get("epochs"), 30)),
            iterations=max(1, _as_int(m.get("iterations"), 300)),
            project=_as_str(m.get("project"), "runs/detect"),
            name=_as_str(m.get("name"), "tune"),
        )


@dataclass(slots=True)
class ModelExportConfig:
    weights_path: str = ""
    format: str = "onnx"
    output_dir: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModelExportConfig:
        m = _mapping(data)
        return cls(
            weights_path=_as_str(m.get("weights_path"), ""),
            format=_as_str(m.get("format"), "onnx"),
            output_dir=_as_str(m.get("output_dir"), ""),
        )


@dataclass(slots=True)
class SahiConfig:
    model_path: str = ""
    source_dir: str = ""
    slice_height: int = 256
    slice_width: int = 256
    overlap_height_ratio: float = 0.2
    overlap_width_ratio: float = 0.2

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SahiConfig:
        m = _mapping(data)
        return cls(
            model_path=_as_str(m.get("model_path"), ""),
            source_dir=_as_str(m.get("source_dir"), ""),
            slice_height=max(1, _as_int(m.get("slice_height"), 256)),
            slice_width=max(1, _as_int(m.get("slice_width"), 256)),
            overlap_height_ratio=_clamp(_as_float(m.get("overlap_height_ratio"), 0.2), 0.0, 0.95),
            overlap_width_ratio=_clamp(_as_float(m.get("overlap_width_ratio"), 0.2), 0.0, 0.95),
        )


@dataclass(slots=True)
class SegIsolationConfig:
    model_path: str = ""
    source_path: str = ""
    output_dir: str = ""
    background: str = "black"
    crop: bool = True

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SegIsolationConfig:
        m = _mapping(data)
        return cls(
            model_path=_as_str(m.get("model_path"), ""),
            source_path=_as_str(m.get("source_path"), ""),
            output_dir=_as_str(m.get("output_dir"), ""),
            background=_as_str(m.get("background"), "black"),
            crop=_as_bool(m.get("crop"), True),
        )


@dataclass(slots=True)
class ModelValidationConfig:
    data_yaml: str = ""
    weights_path: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModelValidationConfig:
        m = _mapping(data)
        return cls(
            data_yaml=_as_str(m.get("data_yaml"), ""),
            weights_path=_as_str(m.get("weights_path"), ""),
        )


@dataclass(slots=True)
class UltralyticsSolutionsConfig:
    solution_type: str = "ObjectCounter"
    model_path: str = ""
    source: str = ""
    output_path: str = ""
    region_points: str = "[(20, 400), (1260, 400)]"
    fps: float = 30.0
    colormap: str = "COLORMAP_JET"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UltralyticsSolutionsConfig:
        m = _mapping(data)
        return cls(
            solution_type=_as_str(m.get("solution_type"), "ObjectCounter"),
            model_path=_as_str(m.get("model_path"), ""),
            source=_as_str(m.get("source"), ""),
            output_path=_as_str(m.get("output_path"), ""),
            region_points=_as_str(m.get("region_points"), "[(20, 400), (1260, 400)]"),
            fps=max(1.0, _as_float(m.get("fps"), 30.0)),
            colormap=_as_str(m.get("colormap"), "COLORMAP_JET"),
        )


@dataclass(slots=True)
class DetectionOutputConfig:
    save_path: str = ""
    save_frames: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DetectionOutputConfig:
        m = _mapping(data)
        return cls(
            save_path=_as_str(m.get("save_path"), ""),
            save_frames=_as_bool(m.get("save_frames"), False),
        )


@dataclass(slots=True)
class IntegrationsConfig:
    # Version of the serialized JSON schema.
    # This is stored at the top-level key "schema_version".
    schema_version: int = 2
    jobs: JobsPolicyConfig = field(default_factory=JobsPolicyConfig)
    albumentations: AlbumentationsConfig = field(default_factory=AlbumentationsConfig)
    comet: CometConfig = field(default_factory=CometConfig)
    dvc: DvcConfig = field(default_factory=DvcConfig)
    sagemaker: SagemakerConfig = field(default_factory=SagemakerConfig)
    kfold: KFoldConfig = field(default_factory=KFoldConfig)
    tuning: TuningConfig = field(default_factory=TuningConfig)
    model_export: ModelExportConfig = field(default_factory=ModelExportConfig)
    sahi: SahiConfig = field(default_factory=SahiConfig)
    seg_isolation: SegIsolationConfig = field(default_factory=SegIsolationConfig)
    model_validation: ModelValidationConfig = field(default_factory=ModelValidationConfig)
    ultralytics_solutions: UltralyticsSolutionsConfig = field(
        default_factory=UltralyticsSolutionsConfig
    )
    detection_output: DetectionOutputConfig = field(default_factory=DetectionOutputConfig)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IntegrationsConfig:
        m = _mapping(data)
        return cls(
            schema_version=_as_int(m.get("schema_version"), 2),
            jobs=JobsPolicyConfig.from_dict(_mapping(m.get("jobs"))),
            albumentations=AlbumentationsConfig.from_dict(_mapping(m.get("albumentations"))),
            comet=CometConfig.from_dict(_mapping(m.get("comet"))),
            dvc=DvcConfig.from_dict(_mapping(m.get("dvc"))),
            sagemaker=SagemakerConfig.from_dict(_mapping(m.get("sagemaker"))),
            kfold=KFoldConfig.from_dict(_mapping(m.get("kfold"))),
            tuning=TuningConfig.from_dict(_mapping(m.get("tuning"))),
            model_export=ModelExportConfig.from_dict(_mapping(m.get("model_export"))),
            sahi=SahiConfig.from_dict(_mapping(m.get("sahi"))),
            seg_isolation=SegIsolationConfig.from_dict(_mapping(m.get("seg_isolation"))),
            model_validation=ModelValidationConfig.from_dict(_mapping(m.get("model_validation"))),
            ultralytics_solutions=UltralyticsSolutionsConfig.from_dict(
                _mapping(m.get("ultralytics_solutions"))
            ),
            detection_output=DetectionOutputConfig.from_dict(_mapping(m.get("detection_output"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
