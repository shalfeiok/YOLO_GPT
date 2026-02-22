# FIX_REPORT

## Summary
Сделан единый исправляющий проход по новым регрессиям: очищен «битый» вывод логов (escape/control символы), восстановлен поток задач (включая training/integrations) и обновление метрик/графика обучения через job events, добавлено корректное завершение обучения и окна визуализации детекции при закрытии приложения, а также централизованный shutdown контейнера и раннеров.

## Issues Found

### Crash / incorrect behavior
- В логах задач отображались управляющие escape-символы (`\x1b...`), что давало «квадратики» и мусор в UI.
- При закрытии приложения обучение могло продолжаться в фоне, а окно визуализации детекции оставалось открытым.

### Jobs
- Для training job не регистрировался `cancel` action в `JobRegistry`, из-за чего управление задачей было неполным.
- После предыдущих изменений данные для training-метрик перестали доходить в UI, т.к. локальная консоль убрана, а парсинг по job events не был подключён.

### Freeze / lifecycle
- Не было централизованного безопасного shutdown фоновых раннеров/контейнера при выходе из приложения.

## Fixes Applied
- `app/core/jobs/process_runner/log_buffer.py`
  - добавлена очистка лог-строк: `strip_ansi` + удаление control chars регулярным выражением;
  - устранён вывод «квадратиков»/мусора в логах задач.
- `app/ui/views/training/view.py`
  - добавлена подписка на `JobLogLine` и `JobProgress` для активной training-задачи;
  - восстановлено обновление метрик/графика через `_on_console_lines_batch` из job log events;
  - добавлен `shutdown()` + `closeEvent()` для остановки обучения и отписки от event bus.
- `app/ui/views/training/view_model.py`
  - training handle теперь регистрирует `cancel` в `job_registry` (`set_cancel`), чтобы корректно работать из «Задач».
- `app/ui/views/detection/view.py`
  - добавлен `shutdown()` + `closeEvent()` с принудительным вызовом `_stop_detection()`;
  - окно визуализации и пайплайн детекции останавливаются при закрытии приложения.
- `app/ui/shell/main_window.py`
  - при закрытии окна теперь вызывается `shutdown()` у созданных вкладок;
  - добавлен вызов `container.shutdown()`.
- `app/application/container.py`
  - добавлен централизованный `shutdown()` (останавливает trainer и гасит job/process runners).
- `app/core/jobs/job_runner.py`, `app/core/jobs/process_runner/runner.py`
  - добавлены методы `shutdown()` для штатного завершения thread/process executors.

## Verification Checklist
- `python -m compileall .`
- `pytest -q`
- `ruff check .`
- `ruff format <changed_files>`

## Manual QA
1. Запустить `python main.py`.
2. Стартовать обучение и убедиться, что:
   - задача появляется во вкладке «Задачи»;
   - логи без мусорных escape-символов;
   - метрики/график на вкладке обучения обновляются.
3. Стартовать детекцию и убедиться, что задача отображается в «Задачах».
4. Закрыть приложение во время активных обучения/детекции:
   - отдельное окно визуализации детекции закрывается;
   - обучение не продолжается в фоне.
5. Проверить, что отмена training из «Задач» работает.
