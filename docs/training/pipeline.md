# Pipeline обучения

## Этапы
1. UI формирует `TrainingConfig` и передаёт в use-case слоя приложения.
2. `TrainModelUseCase` валидирует вход и публикует события.
3. `TrainingService` запускает Ultralytics `YOLO.train(...)` синхронно.
4. Callback на конец эпохи транслирует прогресс.
5. По завершении возвращается путь к `weights/best.pt` (если существует).

## Особенности
- Поддержка advanced options (cache, amp, lr0, mosaic, mixup и др.).
- При `cache=True` workers принудительно `0` (стабилизация на Windows).
- При части ошибок CUDA возможен fallback на CPU.
- Comet/Albumentations интеграции пробрасываются через интеграционный конфиг.
