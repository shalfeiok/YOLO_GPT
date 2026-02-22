# FIX_REPORT

## Summary
Закрыты критические замечания по `JobRunner`: устранена небезопасная глобальная подмена stdout/stderr для многопоточного пула и убран механизм timeout через вложенный поток, который создавал риск thread leaks. Взамен реализован поток-локальный роутер вывода и кооперативный timeout без создания дополнительных потоков.

## Issues Found

### 1) Потокобезопасность `redirect_stdout` в ThreadPool
- Старый код подменял `sys.stdout/sys.stderr` через `contextlib.redirect_stdout`, что в многопоточной среде могло смешивать логи разных jobs.

### 2) Thread leaks при timeout
- Старый код создавал вложенный `Thread` для timeout-ожидания; при зависании в I/O/C-extension поток мог остаться жить в фоне после timeout.

## Fixes Applied
- `app/core/jobs/job_runner.py`
  - добавлен `_ThreadLocalTextRouter` с маршрутизацией вывода по `thread id`;
  - stdout/stderr для конкретной job bind/unbind в рамках worker-thread;
  - сохраняется совместимость с `print(...)` внутри job-функций;
  - удалён вложенный timeout-thread;
  - timeout теперь кооперативный: проверяется до/после выполнения и на каждом progress callback, при превышении публикуется `JobTimedOut` и выставляется cancel token.
- `tests/test_job_runner_thread_local_stdout.py`
  - добавлен тест конкурентного запуска двух jobs с `print(...)`, проверяющий, что логи разделяются по `job_id` и не смешиваются.

## Verification Checklist
- `ruff check .`
- `pytest -q`
- `python -m compileall .`
- `pytest -q tests/test_job_runner_log_batching.py tests/test_job_runner_thread_local_stdout.py`

## Manual QA
1. Запустить 2+ jobs с активным `print(...)` внутри.
2. Проверить Jobs view: лог каждой задачи содержит только свои строки.
3. Запустить job с timeout и убедиться, что статус timeout выставляется, без появления дополнительных зависших потоков от timeout-обертки.
