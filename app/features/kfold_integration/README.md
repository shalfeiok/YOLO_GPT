# K-Fold Cross Validation

Интеграция по [руководству Ultralytics K-Fold](https://docs.ultralytics.com/ru/guides/kfold-cross-validation/).

- Разбиение датасета обнаружения объектов (YOLO format) на K фолдов с помощью `sklearn.model_selection.KFold`.
- Генерация векторов признаков по файлам меток (подсчёт экземпляров по классам), создание папок train/val и data.yaml для каждого фолда.
- Опционально: обучение модели по каждому фолду (веса и параметры задаются в UI).

**Зависимости:** `ultralytics`, `scikit-learn`, `pandas`, `pyyaml`.

Конфиг хранится в `integrations_config.json` (секция `kfold`).
