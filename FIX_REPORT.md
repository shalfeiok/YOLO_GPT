# FIX_REPORT

## Summary
Выполнен единый исправляющий проход по проблемам Jobs/Progress: восстановлена работа политики задач, добавлена корректная регистрация/повтор/отмена jobs для интеграций, улучшено отображение прогресса (в т.ч. для долгих задач без точной доли выполнения), возвращено появление детекции в списке задач и добавлены этапные прогрессы для операций с датасетами.

## Issues Found

### Jobs
- В `IntegrationsActionsMixin` был потерян `_policy_kwargs`, из-за чего часть запусков интеграций могла ломаться до создания jobs.
- `rerun` для jobs интеграций был привязан к «сырому» submit без повторной регистрации handle/действий.
- Детекция не регистрировала cancel-action в registry и не отправляла «живой» progress во время работы.

### Progress
- Progress bar в Jobs часто оставался на 0% для задач с невычислимым прогрессом.
- Dataset операции имели только 0%/100% без промежуточных стадий.

### Policy
- Политика timeout/retry не применялась из-за отсутствующего `_policy_kwargs` в integrations actions.

## Fixes Applied
- `app/ui/views/integrations/view_model_parts/actions.py`
  - восстановлены `_load_jobs_policy()` и `_policy_kwargs()`;
  - добавлен единый `_register_handle()`;
  - `_submit_thread_job()`/`_submit_process_job()` теперь используют общую регистрацию cancel/rerun и корректно повторно создают jobs через те же submit-методы.
- `app/ui/views/jobs/view.py`
  - для running/retrying с 0 прогресса включён indeterminate progress bar (`setRange(0,0)` + "Выполняется…");
  - для известных значений отображается процент в формате.
- `app/ui/views/detection/view.py`
  - при старте детекции регистрируется cancel в `job_registry`;
  - добавлены progress-события в старт/рабочий цикл (через FPS tick), чтобы задача была видна и «живая» в Jobs.
- `app/ui/views/datasets/worker.py`
  - добавлены этапные `progress.emit(...)` для всех операций (prepare/augment/export/merge/rename), чтобы progress bar не стоял на 0 весь runtime.

## Verification Checklist
- `python -m compileall .`
- `pytest -q`
- `ruff check .`
- `ruff format <changed_files>`

## Manual QA
1. Открыть Jobs и запустить операции из Integrations (export/validate/tune/sahi и т.п.) — задачи появляются, policy применяется.
2. Запустить `prepare_yolo`/augment/export classes/merge/rename в Datasets — progress bar показывает промежуточные стадии.
3. Запустить Detection — задача появляется в Jobs, progress не «мертвый» на 0.
4. Проверить Cancel/Retry у интеграционных задач после первого и повторного запуска.
5. Открыть диалог «Политика» в Jobs, изменить значения, запустить новую задачу и убедиться, что timeout/retry применились.
