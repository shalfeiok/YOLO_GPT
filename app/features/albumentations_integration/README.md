# Albumentations integration

Быстрая и гибкая библиотека аугментации изображений. Улучшает обобщающую способность модели за счёт 70+ преобразований. Интеграция с YOLO26 автоматически применяет трансформы при обучении.

- **domain.py** — модель конфига (enabled, use_standard, custom_transforms, p).
- **service.py** — построение списка трансформов для `model.train(augmentations=...)`.
- **repository.py** — чтение/запись секции из общего JSON конфига.
- **ui.py** — виджет секции для вкладки «Интеграции и мониторинг».

Документация: [Ultralytics Albumentations](https://docs.ultralytics.com/ru/integrations/albumentations/).
