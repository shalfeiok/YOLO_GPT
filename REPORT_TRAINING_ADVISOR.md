# REPORT: Советник по обучению

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
- Добавлена новая вкладка UI: `Советник по обучению` с полями путей, режимом «Быстрый анализ/Глубокий анализ», кнопками «Проанализировать», «Экспорт рекомендаций», «Передать в обучение».
- Вкладка обучения получила кнопки:
  - `Применить рекомендации советника`
  - `Отменить применение`
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
1. Откройте вкладку **Советник по обучению**.
2. Укажите:
   - path to `.pt` (обязательно)
   - dataset path (`data.yaml` или корень) (обязательно)
   - run folder (опционально)
   - режим «Быстрый анализ/Глубокий анализ»
3. Нажмите **Проанализировать**.
4. Из отчёта:
   - просмотрите Dataset Health / Run Summary / Model Eval / Recommendations.
   - при необходимости нажмите **Экспорт рекомендаций**.
5. Нажмите **Передать в обучение**.
6. Перейдите во вкладку Training и нажмите **Применить рекомендации советника**.
7. Просмотрите diff-preview и при необходимости откатите через **Отменить применение**.

## Экспорт
- Экспорт делается кнопкой `Экспорт рекомендаций` в выбранный пользователем путь.
- Поддерживается `*.yaml` и `*.json`.

## Примеры предупреждений и изменений
- Class imbalance -> увеличивается `advanced_options.mixup`, сохраняется `mosaic=1.0`.
- BBox out of range / ошибки датасета -> уменьшается агрессивность аугментаций (`mosaic=0`, `mixup=0`).
- Признаки underfitting -> увеличиваются `epochs`, корректируется `advanced_options.lr0`, увеличивается `patience`.
- OOM в артефактах -> уменьшаются `batch/imgsz`, опционально выключается `amp`.
