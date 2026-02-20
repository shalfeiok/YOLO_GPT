# Полное код-ревью: найденные недочеты и рекомендации

## Критические (исправлено)
1. `NameError` в `training`-вкладке: в `app/ui/views/training/sections.py` использовались `MetricsDashboardWidget` и `LogView` без импорта.
2. Несовместимость policy-модели задач: `JobsPolicyDialog` использовал поля `retry_jitter` и `retry_deadline_sec`, которых не было в `JobsPolicyConfig` порта.
3. Несовместимость экспорт-конфига: UI ожидал `model_path`, а доменный `ModelExportConfig` содержит `weights_path`.
4. `IntegrationsViewModel` не имел ряда методов, которые вызывались из UI (`reset_kfold`, `reset_tuning`, `reset_export`, `reset_sahi`, `run_export`, `run_validation`, и т.д.).
5. UI разделов интеграций пытался мутировать immutable/frozen `IntegrationsState` (`ctx.state.* = c`), что приводит к runtime-ошибкам.
6. Ошибки согласованности ключей состояния (`export`/`model_export`, `validation`/`model_validation`, `seg`/`seg_isolation`).

## Средний приоритет (рекомендуется)
1. Провести унификацию naming по всему проекту: `weights_path` vs `model_path` (единый контракт по слоям UI → Application → Features).
2. Добавить unit-тесты на `IntegrationsViewModel` (save/reset/run-ветки + маппинг полей состояния).
3. Добавить smoke-тест на построение UI вкладок `training` и `integrations` (минимум проверка создания виджета без исключений).
4. Убрать дублирование/legacy-алиасы в порте и UI поэтапно, после миграции всех вызовов.

## Низкий приоритет (улучшения)
1. Вынести дефолтные значения reset-конфигов в отдельный слой `defaults` (избежать расхождений между reset и dataclass defaults).
2. Добавить строгую проверку схемы интеграций при загрузке (валидатор + человекочитаемые предупреждения).
3. Добавить линтер-правило/CI-check на "неиспользуемые/несуществующие методы ViewModel из UI".
