# TEST REPORT

Дата: 2026-02-23

## Команда запуска

```bash
pytest -q
```

## Результат

- **133 passed**
- **6 skipped**
- **1 warning**
- Время: ~5.6s

## Что покрыто

### Unit
- `TrainingConfig.validate()` и `diff_training_config()`.
- `settings_diff()` для вложенных структур.
- `DatasetInspector` (битые/пустые/ошибочные labels, imbalance).
- `RunArtifactsReader` (results.csv + args.yaml + missing folder).
- `RecommendationEngine` (несколько эвристических сценариев).
- `ApplyAdvisorRecommendationsUseCase` (apply/undo).

### Integration
- Use-case smoke для `ExportModelUseCase`, `ValidateModelUseCase`.
- Use-case поток `StartDetectionUseCase` + `StopDetectionUseCase` на заглушках адаптеров.
- Существующие интеграционные тесты jobs/event bus/store/use-cases.

### UI smoke
- Проверка создания `MainWindow` (через `importorskip`).

## Что намеренно пропущено

- Полноценные e2e UI тесты: оставлены в виде smoke, чтобы не зависеть от графического окружения/CI.
- Реальный Ultralytics train/inference в тестах не выполняется (используются моки/контрактные заглушки), чтобы тесты оставались быстрыми и воспроизводимыми.

## Замечания по окружению

- В headless окружении отсутствует `libGL.so.1`, поэтому часть Qt-тестов корректно пропускается (`skipped`).
