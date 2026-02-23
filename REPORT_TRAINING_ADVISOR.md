# REPORT: Training Advisor

## Что сделано
- Добавлен `TrainingConfig` (единая типизированная модель параметров обучения), сериализация `to_dict()/to_yaml()`, `validate()`, diff и экспорт в yaml/json.
- Добавлены сервисы советника:
  - `DatasetInspector`
  - `RunArtifactsReader`
  - `ModelEvaluator`
  - `RecommendationEngine`
- Добавлены use-case:
  - `AnalyzeTrainingAndRecommendUseCase`
  - `ApplyAdvisorRecommendationsUseCase` + undo snapshot.
- Добавлен `AdvisorStore` в DI/container для хранения последнего отчёта и рекомендованного конфига.
- Добавлена новая вкладка UI: `Training Advisor` с полями путей, режимом Quick/Deep, Analyze, Export, Send to Training.
- Вкладка обучения получила кнопки:
  - `Apply Advisor Recommendations`
  - `Undo apply`
  - показ preview-diff через диалог.

## Где какие файлы
- Domain:
  - `app/domain/training_config.py`
- Core/Infra:
  - `app/core/training_advisor/models.py`
  - `app/core/training_advisor/dataset_inspector.py`
  - `app/core/training_advisor/run_artifacts_reader.py`
  - `app/core/training_advisor/model_evaluator.py`
  - `app/core/training_advisor/recommendation_engine.py`
- Application:
  - `app/application/use_cases/training_advisor.py`
  - `app/application/advisor_state.py`
  - `app/application/container.py`
- UI:
  - `app/ui/views/training_advisor/view.py`
  - `app/ui/views/training/view.py`
  - `app/ui/views/training/sections.py`
  - `app/ui/shell/stack_controller.py`
  - `app/ui/shell/sidebar.py`
  - `app/ui/shell/main_window.py`

## Как пользоваться
1. Откройте вкладку **Training Advisor**.
2. Укажите:
   - path to `.pt` (обязательно)
   - dataset path (`data.yaml` или корень) (обязательно)
   - run folder (опционально)
   - режим Quick/Deep
3. Нажмите **Analyze**.
4. Из отчёта:
   - просмотрите Dataset Health / Run Summary / Model Eval / Recommendations.
   - при необходимости нажмите **Export recommended config**.
5. Нажмите **Send to Training**.
6. Перейдите во вкладку Training и нажмите **Apply Advisor Recommendations**.
7. Просмотрите diff-preview и при необходимости откатите через **Undo apply**.

## Экспорт
- Экспорт делается кнопкой `Export recommended config` в выбранный пользователем путь.
- Поддерживается `*.yaml` и `*.json`.

## Примеры предупреждений и изменений
- Class imbalance -> увеличивается `advanced_options.mixup`, сохраняется `mosaic=1.0`.
- BBox out of range / ошибки датасета -> уменьшается агрессивность аугментаций (`mosaic=0`, `mixup=0`).
- Признаки underfitting -> увеличиваются `epochs`, корректируется `advanced_options.lr0`, увеличивается `patience`.
- OOM в артефактах -> уменьшаются `batch/imgsz`, опционально выключается `amp`.
