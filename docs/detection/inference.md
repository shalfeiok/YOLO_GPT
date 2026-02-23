# Детекция: запуск инференса

## Поток
1. UI собирает `DetectorSpec` + источник кадров.
2. `StartDetectionUseCase` валидирует и стартует адаптер.
3. Детекция идёт в фоне до `StopDetectionUseCase`.

## Backend
- PyTorch backend
- ONNX backend

Выбор backend зависит от конфигурации и доступности зависимостей.
