"""Composition root / DI container.

UI should not import infrastructure services directly. This container lives in
the application layer and wires up concrete implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.application.ports.capture import CapturePort, FrameSource, FrameSourceSpec
from app.application.ports.detection import DetectionPort, DetectorSpec
from app.application.ports.integrations import IntegrationsPort
from app.application.ports.metrics import MetricsPort
from app.application.use_cases.export_model import DefaultModelExporter, ExportModelUseCase
from app.application.use_cases.integrations_config import (
    DefaultIntegrationsConfigRepository,
    ExportIntegrationsConfigUseCase,
    ImportIntegrationsConfigUseCase,
)
from app.application.use_cases.start_detection import StartDetectionUseCase
from app.application.use_cases.stop_detection import StopDetectionUseCase
from app.application.use_cases.train_model import TrainModelUseCase
from app.application.use_cases.validate_model import DefaultModelValidator, ValidateModelUseCase
from app.config import PROJECT_ROOT
from app.core.events import EventBus
from app.core.jobs import JobRegistry, JobRunner, JsonlJobEventStore, ProcessJobRunner
from app.core.paths import get_app_state_dir
from app.interfaces import IDatasetConfigBuilder, IDetector, ITrainer, IWindowCapture
from app.services import (
    DatasetConfigBuilder,
    TrainingService,
    WindowCaptureService,
)
from app.services.adapters import (
    CaptureAdapter,
    DetectionAdapter,
    IntegrationsAdapter,
    MetricsAdapter,
)

if TYPE_CHECKING:
    from app.ui.infrastructure.notifications import NotificationCenter
    from app.ui.theme.manager import ThemeManager


class Container:
    """Resolves application services. Single place to swap implementations if needed."""

    def __init__(self) -> None:
        self._trainer: ITrainer | None = None
        self._train_model_uc: TrainModelUseCase | None = None
        self._export_model_uc: ExportModelUseCase | None = None
        self._validate_model_uc: ValidateModelUseCase | None = None
        self._start_detection_uc: StartDetectionUseCase | None = None
        self._stop_detection_uc: StopDetectionUseCase | None = None
        self._export_integrations_cfg_uc: ExportIntegrationsConfigUseCase | None = None
        self._import_integrations_cfg_uc: ImportIntegrationsConfigUseCase | None = None
        self._integrations_cfg_repo: DefaultIntegrationsConfigRepository | None = None
        self._event_bus: EventBus | None = None
        self._job_runner: JobRunner | None = None
        self._process_job_runner: ProcessJobRunner | None = None
        self._job_registry: JobRegistry | None = None
        self._detector: IDetector | None = None
        self._detector_onnx: IDetector | None = None
        self._window_capture: IWindowCapture | None = None
        self._dataset_builder: IDatasetConfigBuilder | None = None
        self._theme_manager: ThemeManager | None = None
        self._notifications: NotificationCenter | None = None
        self._capture: CapturePort | None = None
        self._detection: DetectionPort | None = None
        self._metrics: MetricsPort | None = None
        self._integrations: IntegrationsPort | None = None

    @property
    def trainer(self) -> ITrainer:
        if self._trainer is None:
            self._trainer = TrainingService()
        return self._trainer

    @property
    def train_model_use_case(self) -> TrainModelUseCase:
        """Application-layer API for training.

        Prefer this over accessing .trainer directly from UI.
        """

        if self._train_model_uc is None:
            self._train_model_uc = TrainModelUseCase(self.trainer, event_bus=self.event_bus)
        return self._train_model_uc

    @property
    def export_model_use_case(self) -> ExportModelUseCase:
        """Application-layer API for model export."""
        if self._export_model_uc is None:
            self._export_model_uc = ExportModelUseCase(DefaultModelExporter())
        return self._export_model_uc

    @property
    def validate_model_use_case(self) -> ValidateModelUseCase:
        """Application-layer API for model validation."""
        if self._validate_model_uc is None:
            self._validate_model_uc = ValidateModelUseCase(DefaultModelValidator())
        return self._validate_model_uc


    @property
    def start_detection_use_case(self) -> StartDetectionUseCase:
        """Application-layer API for starting detection (validate inputs + load model)."""
        if self._start_detection_uc is None:
            self._start_detection_uc = StartDetectionUseCase(self.detection)
        return self._start_detection_uc

    @property
    def stop_detection_use_case(self) -> StopDetectionUseCase:
        """Application-layer API for stopping detection (best-effort cleanup)."""
        if self._stop_detection_uc is None:
            self._stop_detection_uc = StopDetectionUseCase()
        return self._stop_detection_uc
    @property
    def integrations_config_repo(self) -> DefaultIntegrationsConfigRepository:
        if self._integrations_cfg_repo is None:
            self._integrations_cfg_repo = DefaultIntegrationsConfigRepository()
        return self._integrations_cfg_repo

    @property
    def export_integrations_config_use_case(self) -> ExportIntegrationsConfigUseCase:
        if self._export_integrations_cfg_uc is None:
            self._export_integrations_cfg_uc = ExportIntegrationsConfigUseCase(self.integrations_config_repo)
        return self._export_integrations_cfg_uc

    @property
    def import_integrations_config_use_case(self) -> ImportIntegrationsConfigUseCase:
        if self._import_integrations_cfg_uc is None:
            self._import_integrations_cfg_uc = ImportIntegrationsConfigUseCase(self.integrations_config_repo)
        return self._import_integrations_cfg_uc

    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            self._event_bus = EventBus()
        return self._event_bus

    @property
    def job_runner(self) -> JobRunner:
        """Shared background job runner (thread pool) for long-running tasks."""

        # Ensure JobRegistry subscribes to EventBus before first JobStarted publish.
        # Some jobs are very short-lived; if registry is created after submit(),
        # the Jobs view can miss all events and appear empty.
        _ = self.job_registry
        if self._job_runner is None:
            self._job_runner = JobRunner(self.event_bus)
        return self._job_runner

    @property
    def process_job_runner(self) -> ProcessJobRunner:
        """Background process runner for CPU-heavy / isolated jobs."""

        # Same ordering guarantee as job_runner(): registry must be subscribed first.
        _ = self.job_registry
        if self._process_job_runner is None:
            store = JsonlJobEventStore(get_app_state_dir() / "jobs")
            self._process_job_runner = ProcessJobRunner(self.event_bus, event_store=store)
        return self._process_job_runner

    @property
    def job_registry(self) -> JobRegistry:
        if self._job_registry is None:
            store = JsonlJobEventStore(get_app_state_dir() / "jobs" / "registry.jsonl")
            self._job_registry = JobRegistry(self.event_bus, store=store)
        return self._job_registry

    @property
    def detector(self) -> IDetector:
        """Backwards compatible: PyTorch detector."""
        return self.detection.get_detector(DetectorSpec(engine="pytorch"))

    @property
    def detector_onnx(self) -> IDetector:
        """Backwards compatible: ONNX detector."""
        return self.detection.get_detector(DetectorSpec(engine="onnx"))

    @property
    def window_capture(self) -> IWindowCapture:
        if self._window_capture is None:
            self._window_capture = WindowCaptureService()
        return self._window_capture

    @property
    def dataset_builder(self) -> IDatasetConfigBuilder:
        if self._dataset_builder is None:
            self._dataset_builder = DatasetConfigBuilder()
        return self._dataset_builder

    @property
    def dataset_config_builder(self) -> IDatasetConfigBuilder:
        """Backward-compatible alias used by legacy training view code."""
        return self.dataset_builder

    @property
    def theme_manager(self) -> ThemeManager:
        if self._theme_manager is None:
            raise RuntimeError("ThemeManager must be injected from UI")
        return self._theme_manager

    @theme_manager.setter
    def theme_manager(self, theme_manager: ThemeManager) -> None:
        """Backward-compatible setter for UI code that assigns container.theme_manager."""
        self._theme_manager = theme_manager

    def set_theme_manager(self, theme_manager: ThemeManager) -> None:
        self._theme_manager = theme_manager

    @property
    def notifications(self) -> NotificationCenter:
        if self._notifications is None:
            raise RuntimeError("NotificationCenter must be injected from UI")
        return self._notifications

    @notifications.setter
    def notifications(self, notifications: NotificationCenter) -> None:
        """Backward-compatible setter for UI code that assigns container.notifications."""
        self._notifications = notifications

    def set_notifications(self, notifications: NotificationCenter) -> None:
        self._notifications = notifications

    # --- Paths ---
    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    # --- Ports ---
    @property
    def capture(self) -> CapturePort:
        if self._capture is None:
            self._capture = CaptureAdapter()
        return self._capture

    @property
    def detection(self) -> DetectionPort:
        if self._detection is None:
            self._detection = DetectionAdapter()
        return self._detection

    @property
    def metrics(self) -> MetricsPort:
        if self._metrics is None:
            self._metrics = MetricsAdapter()
        return self._metrics

    @property
    def integrations(self) -> IntegrationsPort:
        if self._integrations is None:
            self._integrations = IntegrationsAdapter()
        return self._integrations

    def create_frame_source(self, source: str | FrameSourceSpec) -> FrameSource:
        """Backwards-compatible helper.

        UI should prefer passing :class:`FrameSourceSpec` through the CapturePort.
        """

        spec = source if isinstance(source, FrameSourceSpec) else FrameSourceSpec(source=source)
        return self.capture.create_frame_source(spec)
