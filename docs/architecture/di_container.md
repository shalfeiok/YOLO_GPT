# DI контейнер

`app/application/container.py` — composition root.

## Что резолвится
- train/export/validate/start_detection/stop_detection use-cases,
- adapters портов (capture/detection/integrations/metrics),
- settings/advisor store,
- Analyze + Apply use-cases советника,
- job/event инфраструктура.

## Важный нюанс
`job_registry` инициализируется до submit задач, чтобы не терять ранние события.
