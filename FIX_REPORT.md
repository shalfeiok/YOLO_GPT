# FIX_REPORT

## Summary
Исправлен краш при закрытии окна/экрана задач: причиной были отложенные UI-callback'и (`QTimer.singleShot`) из job events, которые могли срабатывать уже во время уничтожения `JobsView`. Добавлен безопасный lifecycle-guard и weakref-диспетчер, чтобы никакие обновления UI не выполнялись после начала закрытия виджета.

## Issues Found

### Crash
- `JobsView` продолжал принимать асинхронные события и отложенные callbacks в момент закрытия, что приводило к обращению к закрывающемуся UI.

## Fixes Applied
- `app/ui/views/jobs/view.py`
  - добавлен флаг жизненного цикла `_is_closing`;
  - в `closeEvent` флаг выставляется до отписки от bus;
  - `_on_job_event` теперь использует `weakref` + проверку `_is_closing` перед диспатчем в UI thread;
  - `_on_job_event_ui` также дополнительно guard'ится `_is_closing`.

## Verification Checklist
- `ruff check .`
- `pytest -q`
- `python -m compileall app/ui/views/jobs/view.py`

## Manual QA
1. Запустить приложение, перейти во вкладку Jobs.
2. Запустить любую задачу, чтобы шли progress/log events.
3. Во время поступления событий закрыть окно приложения (или закрыть экран задач, если он открыт отдельно).
4. Убедиться, что краша нет.
