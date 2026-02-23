# Архитектура: слои

## UI (`app/ui`)
Qt views + view model + инфраструктурные адаптеры UI.

## Application (`app/application`)
Use-case слой, settings store, порты, фасады, DI composition root.

## Core (`app/core`)
EventBus, jobs subsystem, observability, training advisor core.

## Services (`app/services`)
Интеграция с Ultralytics, detection/capture adapters, dataset utilities.

## Domain (`app/domain`)
`TrainingConfig` и доменные функции diff/export/validate.
