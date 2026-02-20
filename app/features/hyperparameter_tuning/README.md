# Hyperparameter Tuning (model.tune)

Интеграция по [руководству Ultralytics Hyperparameter Tuning](https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/).

- Запуск `model.tune(data=..., epochs=..., iterations=...)` для генетического поиска по гиперпараметрам (lr0, аугментации и др.).
- Результаты сохраняются в `runs/detect/tune/`: best_hyperparameters.yaml, tune_results.csv, веса best.pt/last.pt.

**Зависимости:** `ultralytics`.

Конфиг хранится в `integrations_config.json` (секция `tuning`).
