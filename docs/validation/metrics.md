# Валидация: метрики и отчёты

## Основные метрики
- mAP50
- loss-компоненты (в training артефактах)

## Источники данных
- `results.csv` из runs
- результаты model validation use-case

## Практика интерпретации
- Низкий mAP50 + высокий loss => возможный underfitting.
- Низкий mAP50 + низкий loss => риск overfitting/проблем датасета.
