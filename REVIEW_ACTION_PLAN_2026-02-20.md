# Полный план улучшений проекта YOLO Desktop Studio (восстановленная версия)

_Обновлено: 2026-02-20._

Этот файл возвращает и фиксирует подробный план из полного ревью: что делать, в каком порядке и как проверять результат.

---

## 1) Executive Summary

### Что уже хорошо
- Есть разделение на слои: UI (`app/ui`), application use-cases (`app/application/use_cases`), сервисы/адаптеры (`app/services`), core (`app/core`).
- Есть базовая инженерная дисциплина: `ruff`, `black`, `mypy`, `pytest`, `coverage`, CI workflow.
- Есть инфраструктура фоновых задач: `EventBus`, `JobRunner`, `ProcessJobRunner`, `JobRegistry`.

### Главные проблемы (фокус)
1. Архитектурный дрейф между документацией и фактическим кодом.
2. Большой технический долг в lint/type (не весь проект стабильно «зелёный»).
3. Слишком крупные UI-модули (особенно Detection View) с высокой связанностью.
4. Риски в надежности/ошибках на границах UI/потоки/интеграции.
5. Безопасность generated-script сценариев требует ужесточения.

### Топ-5 самых ценных улучшений
1. Стабилизировать quality gates для core+application (lint/type/tests).
2. Декомпозировать `DetectionView` на presenter/controller/pipeline service.
3. Унифицировать error handling с явной таксономией ошибок.
4. Укрепить security для subprocess/generated scripts.
5. Синхронизировать документацию/онбординг с текущим кодом.

---

## 2) Target Architecture (без big-bang)

### Текущее состояние (кратко)
- `main.py` создаёт Qt app, DI container, main window.
- `Container` собирает сервисы/use-cases и адаптеры.
- UI в ряде мест совмещает представление + orchestration + I/O.

### Целевая модель
- **UI слой**: только виджеты, отображение state, user intents.
- **Application слой**: use-cases + контракты + orchestration.
- **Infrastructure/services**: внешние SDK/OS/subprocess и адаптеры.
- **Core**: events, jobs, errors, observability.

### Правила зависимостей
- UI → Application (ports/use-cases)
- Application → Ports → Adapters
- UI не импортирует инфраструктурные детали напрямую (кроме composition root).

### Итеративная миграция
1. Stabilize (P0): quality gates + критичные баги надежности.
2. Decouple (P1): вынос orchestration из тяжёлых view.
3. Harden (P1): security + deterministic error handling.
4. Optimize (P2): perf метрики, UX speedups, polish.

---

## 3) Приоритетный backlog (P0/P1/P2)

| ID | Приоритет | Область | Задача | Сложность | Риск |
|---|---|---|---|---|---|
| A-01 | P0 | Качество | Сделать `ruff`/`mypy` зелёными для `app/core` и `app/application` | M | Med |
| A-02 | P0 | Надёжность | Привести smoke/headless сценарии к стабильному запуску | S | Low |
| A-03 | P0 | Тесты | Добавить регрессионные тесты на job timeout/cancel/retry | M | Med |
| A-04 | P1 | Архитектура | Разбить `app/ui/views/detection/view.py` на модули | L | Med |
| A-05 | P1 | Безопасность | Санитизация/валидация входов для generated scripts | M | High |
| A-06 | P1 | Error handling | Ввести единую таксономию ошибок + user-safe сообщения | M | Med |
| A-07 | P1 | DX | Подключить/усилить pre-commit policy | S | Low |
| A-08 | P1 | Документация | Синхронизировать docs с фактической архитектурой | S | Low |
| A-09 | P2 | Производительность | Ввести измерения latency/drop frames в detection pipeline | M | Med |
| A-10 | P2 | UX | Добавить wizard проверки окружения (GPU/ONNX/CUDA) | M | Med |

---

## 4) Top-20 мест для исправления (сначала)

1. `app/ui/views/detection/view.py` — декомпозиция класса.
2. `app/ui/views/training/view.py` — отделить UI от orchestration.
3. `app/ui/views/training/advanced_settings_dialog.py` — типизация/контракты виджетов.
4. `app/core/jobs/process_job_runner.py` — строгая типизация multiprocessing.
5. `app/core/jobs/job_runner.py` — закрыть edge-cases timeout/cancel.
6. `app/core/jobs/job_event_store.py` — корректность сериализации dataclass/event.
7. `app/ui/components/log_model.py` — сигнатуры Qt model override.
8. `app/ui/infrastructure/settings.py` — согласовать return types.
9. `app/ui/infrastructure/notifications.py` — убрать спорные аннотации/ignores.
10. `app/ui/infrastructure/file_dialogs.py` — аналогично по typing.
11. `app/services/capture_service.py` — platform guards + windows typing.
12. `app/features/ultralytics_solutions/service.py` — security hardening.
13. `app/features/detection_visualization/backends/opencv_backend.py` — undefined names/typing.
14. `app/application/facades/integrations.py` — нормализовать import/style.
15. `app/application/container.py` — поддерживать чистый composition root.
16. `main.py` — минимизировать bootstrap side-effects.
17. `docs/development.md` — актуализировать инструкции.
18. `ARCHITECTURE.md` — убрать устаревшие ссылки и рассинхрон.
19. `.github/workflows/ci.yml` — quality-ratchet и staged strictness.
20. `requirements*.txt` — strategy pinning/constraints для воспроизводимости.

---

## 5) Надёжность и обработка ошибок (стандарт)

### Категории ошибок
- `ValidationError` (входные данные пользователя)
- `DomainError` (нарушение бизнес-правил)
- `IntegrationError` (внешняя библиотека/API)
- `InfrastructureError` (FS/OS/network/process)
- `InternalError` (непредвиденная ошибка)

### Правила
- На use-case boundary: нормализовать ошибку и контекст.
- В UI: показывать безопасное сообщение + actionable hint.
- В логах: обязательные поля `event`, `component`, `operation`, `error_type`.

### DoD
- Все пользовательские ошибки имеют понятные тексты.
- Трассировки остаются в логах, но не «текут» в UI как сырые stacktrace.

---

## 6) Производительность

### Где мерить
- Detection: `capture_ms`, `inference_ms`, `render_ms`, dropped frames.
- Training: latency UI-логов, responsiveness при длинных эпохах.

### План
1. Добавить профилирование hot path (sampling profiler).
2. Добавить метрики очередей и лагов.
3. Ввести perf-regression smoke сценарии.

### DoD
- Есть базовые численные KPI по latency/FPS.
- PR не ухудшает KPI больше заданного порога.

---

## 7) Безопасность

### Риски
- Запуск generated scripts из пользовательских конфигов.
- Слабый pinning зависимостей.
- Отсутствие обязательного security scan в CI.

### Действия
1. Валидация структуры/типов входов для script generation.
2. Ограничить subprocess окружение, timeout, рабочую директорию.
3. Добавить `pip-audit`/`bandit` в CI.

### DoD
- Невалидные/подозрительные payload блокируются тестами.
- Security job в CI обязателен для merge.

---

## 8) Тестовая стратегия

### Минимальный safety-net на 1–2 дня
1. Regresison test: import/package headless safety.
2. Job runner tests: timeout/cancel/retry determinism.
3. Detection config parsing tests (валидные/невалидные).
4. Integrations config migration tests.

### DoD
- Критичные сценарии закрыты тестами и повторяемы локально/в CI.

---

## 9) DevEx / CI / Release

### Рекомендации
- `pre-commit`: ruff, black, mypy (по изменённым путям), pytest smoke.
- CI: линт → типы → unit/integration → packaging smoke.
- Ветвление/релизы: conventional commits + semver + changelog.

### DoD
- Новые PR не ухудшают quality baseline.
- Релизный процесс воспроизводим и документирован.

---

## 10) Quick Wins (сразу)

1. Закрыть оставшиеся P0 lint/type в core/application.
2. Проставить platform markers для OS-специфичных тестов.
3. Упростить и разделить heavy view modules.
4. Подчистить документацию и onboarding команды.
5. Подключить security scan в workflow.

---

## 11) Пошаговый план выполнения (первые 2 спринта)

### Спринт 1 (стабилизация)
- A-01, A-02, A-03, A-07, A-08
- Результат: стабильный baseline, предсказуемый CI, актуальные docs.

### Спринт 2 (архитектура и hardening)
- A-04, A-05, A-06 + старт A-09
- Результат: ниже связность UI, выше надёжность и безопасность.

---

## Definition of Done (общий)

- CI green на целевых quality gates.
- Все новые/исправленные сценарии покрыты тестами.
- Документация обновлена вместе с кодом.
- Нет новых критичных security findings.

