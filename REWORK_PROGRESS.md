# REWORK PROGRESS
Baseline plan: REWORK_PLAN.md (v1.0)
Last updated: 2026-02-20
Legend: [ ] not started, [~] in progress, [x] done

## Checklist (from REWORK_PLAN.md)
- [x] `TrainingViewModel`: `daemon=False`, добавить `self._training_thread.join(timeout=...)` при finish/cancel.
- [x] `TrainingViewModel`: логировать exception в run() через `logging.getLogger(__name__).exception(...)`.
- [x] `TrainModelUseCase`: гарантировать `TrainingFailed` при любых ошибках (уже есть), но дополнить fallback на ошибки в UI-thread boundary. (исправлено: cancel не публикует TrainingFinished)
- [x] `TrainingService`: сделать редирект stdout/stderr **опциональным** и безопасным (контекст-менеджер, блокировка на время training, предупреждение если уже редирект активен).
- [x] Вынести `system_metrics` за UI: UI использует `Container.metrics` (MetricsPort), без импорта infrastructure.
- [x] Для datasets/detection: внедрить use-cases `ScanDatasets`, `ImportDataset`, `StartDetection`, `StopDetection` и т.п.
- [x] UI refactor: убраны прямые импорты `app.services.*` из UI (datasets/detection/training + DI shim). Следующий шаг: заменить фасады на полноценные use-cases/ports.
- [ ] Сформировать “UI component library” (у вас уже есть `app/ui/components/*`) и довести до системного использования.
- [x] Capture boundary: UI больше не импортирует `OpenCVFrameSource`; создание источника кадров через `Container.create_frame_source()` + `FrameSource` Protocol.
- [ ] Для каждого монолита: цель — **≤ 250–350 LOC на файл**, остальное — компоненты.
- [x] Заменить `except Exception: pass` на `except Exception as e: log.debug(..., exc_info=e)` там, где интеграция опциональная.
- [ ] Добавить correlation id / run id для обучения и детекции (в extra поля логов).
- [ ] `features/integrations_config`: добавить версионирование и миграции.
- [ ] Валидировать пути (dataset yaml, weights), device строки и т.п.
- [~] Вынести Ports: `DetectionPort`, `CapturePort`, `MetricsPort`, `IntegrationsPort`.
  - [x] `CapturePort` + `FrameSourceSpec` + infra adapter (`CaptureAdapter`) + wiring в `Container`.
  - [x] `DetectionPort` + infra adapter (`DetectionAdapter`) + wiring в `Container` + UI switch.
  - [x] `MetricsPort` + infra adapter (`MetricsAdapter`) + wiring в `Container` + UI training metrics.
  - [x] `IntegrationsPort` + infra adapter (`IntegrationsAdapter`) + wiring в `Container` + UI integrations/jobs policy.
- [ ] Нормализовать результат/ошибки: Result/Either или исключения на границе use-case.
- [x] Unit-тесты `TrainModelUseCase` (success/fail/cancel).
- [ ] Тесты `TrainingViewModel`: что сигналы эмитятся и таймер останавливается.
- [x] Smoke tests: boot UI без GPU/без comet/без albumentations. (imports guarded; added test blocking optional deps)
- [ ] VM: lifecycle thread (non-daemon, join, state machine: IDLE/RUNNING/STOPPING)
- [ ] VM: запрет параллельных стартов + понятное сообщение
- [ ] Service: безопасный stdout/stderr redirect (context manager + lock)
- [ ] Use-case: расширить события (TrainingStarted уже есть) → добавить run_id
- [ ] Метрики: вынести парсинг в отдельный сервис и покрыть тестами
- [x] Разделить `detection/view.py` на панели/компоненты (вынесено UI build в `app/ui/views/detection/sections.py`)
- [ ] Вынести запуск/остановку детекции в `StartDetectionUseCase`
- [ ] Стандартизировать backends (onnx/torch/etc.) как порты
- [ ] Ограничить частоту обновления preview
- [x] Разделить `integrations/view.py` на независимые панели (вынесено в `app/ui/views/integrations/sections.py`)
- [x] Разделить `training/view.py` на панели/компоненты (вынесено UI build в `app/ui/views/training/sections.py`)
- [x] Разделить `training/advanced_settings_dialog.py` на секции/компоненты (вынесено в `app/ui/views/training/advanced_settings/sections.py`).
- [ ] Конфиг: schema + миграции + “Validate & Test connection” actions
- [ ] Убрать silent-fail в интеграциях, добавить user-facing status
- [ ] Use-case для сканирования/импорта/валидации датасетов
- [ ] Валидация data.yaml и структуры директорий
- [ ] Кэширование списка датасетов
- [ ] Единый формат логов (JSON optional), run_id корреляция
- [ ] ErrorBoundary: кнопка “Copy stacktrace”, “Open logs”
- [ ] Метрики производительности (timed) расширить на детекцию/захват
- [ ] CI pipeline (ruff, pytest, mypy for core/application)
- [ ] Pre-commit: ensure hooks cover ruff+black
- [ ] Test matrix: Windows/Linux (минимум smoke)

### P0 – Detection runner
- [~] DetectionRunner: вынести threads/capture/inference из DetectionView в отдельный класс (runner.py добавлен, wiring в UI следующим шагом)
