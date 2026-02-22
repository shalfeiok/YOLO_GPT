# FIX_REPORT

## Summary
Исправлен краш при одновременном запуске нескольких действий: причиной были небезопасные UI-обновления из не-UI потоков в Jobs/Training. Все обработчики событий, приходящие из worker/process потоков, теперь маршалятся на главный Qt-поток через `QTimer.singleShot(0, ...)`, что стабилизирует приложение под параллельной нагрузкой.

## Issues Found

### Crash
- `JobsView` обрабатывал `JobLogLine` и обновлял `QTextEdit` напрямую из callback event bus (потенциально не UI thread).
- `TrainingView` обновлял прогресс/метрики напрямую из callback `JobProgress`/`JobLogLine` (также потенциально не UI thread).

### Concurrency
- При одновременных задачах частота событий выше, из-за чего race/thread-affinity нарушения проявлялись чаще и приводили к падению.

## Fixes Applied
- `app/ui/views/jobs/view.py`
  - `_on_job_event` переведён в thread-safe диспетчер: любое событие сначала перекидывается в UI thread;
  - добавлен `_on_job_event_ui` для всей дальнейшей логики обновления лога/таблицы.
- `app/ui/views/training/view.py`
  - `JobProgress` и `JobLogLine` теперь обрабатываются через `QTimer.singleShot(0, ...)`;
  - обновления виджетов прогресса/метрик выполняются строго на главном потоке.

## Verification Checklist
- `python -m compileall .`
- `pytest -q`
- `ruff check .`
- `ruff format app/ui/views/jobs/view.py app/ui/views/training/view.py`

## Manual QA
1. Запустить приложение и параллельно запустить несколько действий (например, dataset + detection + integrations job).
2. Убедиться, что UI не падает при интенсивном поступлении логов/progress.
3. Проверить, что лог в Jobs продолжает обновляться realtime.
4. Проверить, что прогресс обучения/метрики продолжают обновляться без крашей.
