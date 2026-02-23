from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.advisor_state import TrainingConfigTarget
from app.core.training_advisor.dataset_inspector import DatasetInspector
from app.core.training_advisor.model_evaluator import ModelEvaluator
from app.core.training_advisor.models import AdvisorReport
from app.core.training_advisor.recommendation_engine import RecommendationEngine
from app.core.training_advisor.run_artifacts_reader import RunArtifactsReader
from app.domain.training_config import TrainingConfig, diff_training_config


@dataclass(frozen=True, slots=True)
class AnalyzeTrainingRequest:
    model_weights_path: Path
    dataset_path: Path
    run_folder_path: Path | None
    mode: str
    current_training_config: TrainingConfig


class AnalyzeTrainingAndRecommendUseCase:
    def __init__(
        self,
        dataset_inspector: DatasetInspector,
        run_reader: RunArtifactsReader,
        model_evaluator: ModelEvaluator,
        recommendation_engine: RecommendationEngine,
    ) -> None:
        self._dataset_inspector = dataset_inspector
        self._run_reader = run_reader
        self._model_evaluator = model_evaluator
        self._recommendation_engine = recommendation_engine

    def execute(self, request: AnalyzeTrainingRequest) -> AdvisorReport:
        ds_yaml = request.dataset_path if request.dataset_path.suffix in {".yaml", ".yml"} else request.dataset_path / "data.yaml"
        dataset_health = self._dataset_inspector.inspect(request.dataset_path)
        run_summary = self._run_reader.read(request.run_folder_path)
        model_eval = self._model_evaluator.evaluate(request.model_weights_path, ds_yaml, request.run_folder_path or Path("runs/train"))
        recommended_cfg, items, diff, deep_warnings = self._recommendation_engine.recommend(
            request.current_training_config,
            dataset_health,
            run_summary,
            model_eval,
            mode=request.mode,
        )
        warnings = dataset_health.get("warnings", []) + run_summary.get("warnings", []) + model_eval.get("warnings", []) + deep_warnings
        errors = dataset_health.get("errors", [])
        return AdvisorReport(
            dataset_health=dataset_health,
            run_summary=run_summary,
            model_eval=model_eval,
            recommendations=items,
            recommended_training_config=recommended_cfg,
            diff=diff,
            warnings=warnings,
            errors=errors,
        )


class ApplyAdvisorRecommendationsUseCase:
    def __init__(self) -> None:
        self._undo_snapshot: TrainingConfig | None = None

    def execute(self, recommended_training_config: TrainingConfig, target: TrainingConfigTarget) -> list[dict]:
        current = TrainingConfig.from_current_state(target.get_current_training_state())
        self._undo_snapshot = current
        target.apply_training_state(recommended_training_config.to_dict())
        return diff_training_config(current, recommended_training_config)

    def undo(self, target: TrainingConfigTarget) -> list[dict]:
        if self._undo_snapshot is None:
            return []
        now = TrainingConfig.from_current_state(target.get_current_training_state())
        target.apply_training_state(self._undo_snapshot.to_dict())
        return diff_training_config(now, self._undo_snapshot)
