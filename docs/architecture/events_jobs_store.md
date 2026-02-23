# EventBus, Jobs и Store настроек

## EventBus
Паблиш/сабскрайб доменных и job-событий.

## JobRegistry
- хранит snapshot задач,
- реплеит события из jsonl,
- поддерживает retry/cancel semantics.

## AppSettingsStore
- immutable snapshots (`AppSettings` dataclasses),
- update/reset,
- валидация training конфигурации,
- publish событий изменения (например `training_changed`).

## Diff
- `settings_diff` и `diff_training_config` используются для показа того, что изменил советник.
