# REPORT: Settings Single Source of Truth

## 1) Audit (inventory)

| Параметр | Где задавался раньше | Где используется теперь |
|---|---|---|
| `training.dataset_paths` | `TrainingView` (QLineEdit rows) | `AppSettingsStore.training.dataset_paths` (UI read/write + training start snapshot) |
| `training.model_name`, `weights_path` | `TrainingView` combo + weights edit | `AppSettingsStore.training` |
| `training.epochs/batch/imgsz/patience/workers/optimizer/device/project` | `TrainingView` (спинбоксы/инпуты) | `AppSettingsStore.training` |
| `training.advanced_options` | локальное поле `TrainingView._advanced_options` | `AppSettingsStore.training.advanced_options` |
| Advisor current training config | `Container.last_training_state` | snapshot из `AppSettingsStore.training` |
| Apply/undo advisor recommendations | прямое изменение UI target | `ApplyAdvisorRecommendationsUseCase` обновляет `AppSettingsStore` |
| `detection.confidence/iou` | дефолты в detection tab | дефолтные typed-поля в `AppSettings` (интеграция вкладки может постепенно расширяться) |
| Validation/Dataset/Integrations/UI prefs | разрозненные модули/дефолты | typed секции в `AppSettings` как единая модель |

## 2) New architecture

- Application layer:
  - `app/application/settings/models.py` — typed dataclasses (`AppSettings`, `TrainingSettings`, ...).
  - `app/application/settings/store.py` — in-memory singleton store, atomic updates, reset, pub/sub.
  - `app/application/settings/diff.py` — единый flat diff util.
- DI:
  - `Container.settings_store` — singleton in-memory source of truth.
- UI adapter:
  - `SettingsController` (UI infrastructure) скрывает внутренности store от views.

## 3) Event model

- Topics:
  - `training_changed`
  - `detection_changed`
  - `settings_changed`
- Subscribe:
  - `unsubscribe = store.subscribe("training_changed", callback)`
  - `unsubscribe()` при shutdown.

## 4) Rules for adding new settings

1. Добавить typed-поле в `models.py` в нужный домен.
2. Добавить/расширить update-method в `AppSettingsStore` + валидацию.
3. UI читает initial state из `SettingsController.snapshot()/training()`.
4. UI пишет только через `SettingsController.update_*`.
5. Long-running use-cases получают snapshot из store в момент запуска.

## 5) Session lifecycle

- Store живёт только в памяти процесса.
- На старте: инициализация from defaults (`AppSettings.default()`).
- На перезапуске приложения: state reset к дефолтам автоматически (без disk persistence).
