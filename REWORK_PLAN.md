# План реворка и code review (YOLO Trainer & Real-Time Detection)

Дата: 2026-02-20  
Репозиторий: Myapp (архив Myapp.zip)

## 0) Executive summary

Проект уже имеет сильную базу: слоистая архитектура (UI → Application → Services → Domain), EventBus для событий обучения, конфиги качества (ruff/black/mypy/pytest), тесты и довольно много готового функционала (обучение, детекция, интеграции, метрики).

Главные риски/узкие места сейчас — **монолитные Qt-экраны по 700–1200 LOC**, **не до конца выдержанные границы слоёв (UI импортирует Services напрямую)**, **потоки/остановка обучения сделаны “по минимуму” (daemon-thread без join, слабая отмена/cleanup)**, **логирование/обработка ошибок местами “проглатывается”**, а также **смешение ответственности (UI вычисляет системные метрики и т.п.)**.

Ниже — полный план улучшений с приоритетами и конкретными задачами.

---

## 1) Быстрый аудит структуры

**Кодовая база (примерно):**
- Python файлов: ~200 (app: ~171, tests: ~15, examples: ~13)
- Строк кода (py): ~19.5k
- Самые крупные файлы:
  - `app/ui/views/integrations/view.py` (~1268)
  - `app/ui/views/detection/view.py` (~1238)
  - `app/ui/views/training/view.py` (~788)
  - `app/ui/views/training/advanced_settings_dialog.py` (~761)

**Текущая архитектура (по ARCHITECTURE.md):**
- UI (PySide6) → Application (use cases) → Services/Infrastructure → Domain
- Правило: UI не должен напрямую импортировать feature-level services.

**Найденные нарушения границы слоя (UI → Services):**
- `app/ui/infrastructure/di.py`
- `app/ui/views/datasets/view.py`
- `app/ui/views/datasets/worker.py`
- `app/ui/views/detection/view.py`
- `app/ui/views/training/view.py` (например `app.services.system_metrics`)

---

## 2) Что уже хорошо (оставляем и усиливаем)

1. **EventBus + события обучения** (`TrainingProgress/Finished/Failed/Cancelled`) — хорошая “шина” между слоями.
2. **Use-case `TrainModelUseCase`** — правильный Application слой.
3. **Инструменты качества**: ruff/black/mypy/pytest/coverage конфиги уже есть — это ускоряет доводку до “production-grade”.
4. **Отдельный сервис обучения** (`TrainingService`) синхронный — правильно: потоки держать в VM/app-слое.
5. **Интеграции (Comet/Albumentations)** уже структурированы как features.

---

## 3) Критические проблемы (P0) и как исправить

### P0.1 — Потоки и жизненный цикл обучения (stop/cleanup)
**Сейчас:**
- `TrainingViewModel` запускает `Thread(..., daemon=True)` и **не делает join**.
- `stop_training()` только зовёт `use_case.stop()`.
- Любые исключения в worker-потоке “глушатся” (catch Exception, `_ = e`), без логирования.
- stdout/stderr редиректится в `TrainingService`. Это глобальное состояние процесса → потенциально опасно при параллельных операциях.

**Что сделать:**
- Сделать thread **не-daemon**, хранить state и **join** на завершение/остановку (с таймаутом).
- Ввести явный протокол **cancellation**:
  - use-case stop() → trainer.stop() → callback/исключение StopTrainingRequested → publish TrainingCancelled.
- Убрать “проглатывание” исключений: логировать и гарантировать публикацию `TrainingFailed`.
- Защититься от повторного старта обучения (idempotency): запретить старт если training активен, вернуть понятную ошибку в UI.

**Задачи:**
- [ ] `TrainingViewModel`: `daemon=False`, добавить `self._training_thread.join(timeout=...)` при finish/cancel.
- [ ] `TrainingViewModel`: логировать exception в run() через `logging.getLogger(__name__).exception(...)`.
- [ ] `TrainModelUseCase`: гарантировать `TrainingFailed` при любых ошибках (уже есть), но дополнить fallback на ошибки в UI-thread boundary.
- [ ] `TrainingService`: сделать редирект stdout/stderr **опциональным** и безопасным (контекст-менеджер, блокировка на время training, предупреждение если уже редирект активен).

---

### P0.2 — Архитектурные границы (UI импортирует Services)
**Сейчас:**
- UI напрямую тянет `app.services.*` (особенно `system_metrics` и части dataset/detection).
- Это приводит к сложной тестируемости и “липкости” UI к инфраструктуре.

**Что сделать:**
- Для всего, что вызывает внешний мир (метрики, файловая система, GPU info, загрузка датасетов, детекция) — сделать **Application/use-case слой** или **UI-порт** через Container (DI).
- UI должен зависеть от абстракций/портов, а не от services.

**Задачи:**
- [ ] Вынести `system_metrics` за UI: сделать `GetSystemMetricsUseCase` (или `SystemMetricsPort` в контейнере).
- [ ] Для datasets/detection: внедрить use-cases `ScanDatasets`, `ImportDataset`, `StartDetection`, `StopDetection` и т.п.
- [ ] UI refactor: заменить прямые импорты services на вызовы container.*use_case.

---

### P0.3 — Монолитные Qt Views (1200 LOC)
**Сейчас:** файлы `integrations/view.py`, `detection/view.py`, `training/view.py` огромные; в них смешаны:
- layout + виджеты
- валидация
- форматирование
- часть бизнес-логики/инфраструктуры

**Что сделать:**
- Разделить каждый экран на **модули-компоненты** (widgets) + view-model + presenters.
- Вынести табы/панели/диалоги в отдельные классы:
  - `DetectionView`: SourcePanel, ModelPanel, ControlsPanel, PreviewPanel, StatsPanel, etc.
  - `IntegrationsView`: CometPanel, DVCPanel, AlbumentationsPanel, SagemakerPanel, Save/LoadPanel
  - `TrainingView`: DatasetPanel, ParamsPanel, AdvancedDialog, ProgressPanel, ConsolePanel, MetricsPanel

**Задачи:**
- [ ] Сформировать “UI component library” (у вас уже есть `app/ui/components/*`) и довести до системного использования.
- [ ] Для каждого монолита: цель — **≤ 250–350 LOC на файл**, остальное — компоненты.

---

## 4) Важные улучшения (P1)

### P1.1 — Логирование, диагностика, ошибка-границы
**Сейчас:** часть ошибок “съедается” `except Exception: pass` (например в `TrainingService` интеграции).
**Что сделать:**
- Ввести единый helper: `log_exception(context, extra=...)`.
- В местах “optional integration” — ловить конкретные исключения и логировать на debug/info.
- В UI: централизованный `ErrorBoundary` уже подключается в main — расширить: показывать user-friendly сообщения + action (“Open logs”, “Copy details”).

**Задачи:**
- [ ] Заменить `except Exception: pass` на `except Exception as e: log.debug(..., exc_info=e)` там, где интеграция опциональная.
- [ ] Добавить correlation id / run id для обучения и детекции (в extra поля логов).

---

### P1.2 — Конфигурация: единый источник правды + валидация
**Сейчас:** много констант (`app/config.py`, `app/models.py`) + интеграции читают свои конфиги.
**Что сделать:**
- Ввести `AppConfig` (pydantic/dataclasses) с:
  - defaults
  - schema validation
  - миграции версий конфигов (если формат меняется)
- Развести:
  - runtime state (последние пути/окна) — в settings storage
  - project config (интеграции, тренировка) — в конфиг проекта

**Задачи:**
- [ ] `features/integrations_config`: добавить версионирование и миграции.
- [ ] Валидировать пути (dataset yaml, weights), device строки и т.п.

---

### P1.3 — API контракт между слоями (типизация/протоколы)
**Что сделать:**
- Описать порты (Protocols) на границе Application↔Services (как уже сделано для TrainerPort).
- Для детекции/захвата/интеграций тоже.

**Задачи:**
- [ ] Вынести Ports: `DetectionPort`, `CapturePort`, `MetricsPort`, `IntegrationsPort`.
- [ ] Нормализовать результат/ошибки: Result/Either или исключения на границе use-case.

---

### P1.4 — Тесты: расширить покрытие на сценарии UI↔Application
**Сейчас:** есть тесты, но стоит усилить:
- отмена обучения
- ошибки тренера
- корректная публикация событий
- конфиги интеграций

**Задачи:**
- [ ] Unit-тесты `TrainModelUseCase` (success/fail/cancel).
- [ ] Тесты `TrainingViewModel`: что сигналы эмитятся и таймер останавливается.
- [ ] Smoke tests: boot UI без GPU/без comet/без albumentations.

---

## 5) Улучшения (P2): UX/Performance/Packaging

### P2.1 — Производительность UI
- Снизить частоту обновлений там, где не нужно (метрики 1s ок; превью — адаптивно).
- Для графиков — буферизация точек и downsampling.
- Нормализовать работу с изображениями (copy vs view).

### P2.2 — Packaging/Distribution
- Проверить `packaging/` и `.spec` (PyInstaller?) на reproducible build.
- Добавить CI workflow:
  - ruff, mypy (частично), pytest
  - build artifacts (опционально)

### P2.3 — Документация
- Дополнить ARCHITECTURE: схемы потоков, жизненный цикл обучения, контракт событий.
- Добавить `CONTRIBUTING.md`: как запускать, как форматировать, как релизить.

---

## 6) План работ по этапам (roadmap)

### Этап A (1–2 дня): стабилизация P0
- Потоки обучения (join, отмена, логирование)
- Убрать прямые UI→Services импорты в самых проблемных местах (training/detection)
- Разбить самый большой экран (начать с `training/view.py`)

### Этап B (3–5 дней): архитектура и тесты (P1)
- Use-cases/ports для datasets/detection/metrics
- Нормализовать конфиги
- Добавить ключевые unit tests

### Этап C (1–2 недели): “best-in-class” UI/UX + packaging
- Полный refactor остальных монолитов
- Улучшения производительности
- CI/CD + сборка + документация

---

## 7) Детальный backlog задач (копируем в трекер)

### Training
- [ ] VM: lifecycle thread (non-daemon, join, state machine: IDLE/RUNNING/STOPPING)
- [ ] VM: запрет параллельных стартов + понятное сообщение
- [ ] Service: безопасный stdout/stderr redirect (context manager + lock)
- [ ] Use-case: расширить события (TrainingStarted уже есть) → добавить run_id
- [ ] Метрики: вынести парсинг в отдельный сервис и покрыть тестами

### Detection
- [ ] Разделить `detection/view.py` на панели/компоненты
- [ ] Вынести запуск/остановку детекции в `StartDetectionUseCase`
- [ ] Стандартизировать backends (onnx/torch/etc.) как порты
- [ ] Ограничить частоту обновления preview

### Integrations
- [ ] Разделить `integrations/view.py` на независимые панели
- [ ] Конфиг: schema + миграции + “Validate & Test connection” actions
- [ ] Убрать silent-fail в интеграциях, добавить user-facing status

### Datasets
- [ ] Use-case для сканирования/импорта/валидации датасетов
- [ ] Валидация data.yaml и структуры директорий
- [ ] Кэширование списка датасетов

### Core/Observability
- [ ] Единый формат логов (JSON optional), run_id корреляция
- [ ] ErrorBoundary: кнопка “Copy stacktrace”, “Open logs”
- [ ] Метрики производительности (timed) расширить на детекцию/захват

### QA/CI
- [ ] CI pipeline (ruff, pytest, mypy for core/application)
- [ ] Pre-commit: ensure hooks cover ruff+black
- [ ] Test matrix: Windows/Linux (минимум smoke)

---

## 8) Definition of Done для “лучшего проекта”

- Архитектура выдержана (UI не импортирует services напрямую)
- Каждый экран ≤ 350 LOC + компоненты
- Training/Detection устойчивы: отмена, ошибки, повторный запуск
- Логи понятные, воспроизводимые, с run_id
- Тесты покрывают критические сценарии, CI зелёный
- Документация: quickstart + architecture + contributing + release

