# SAHI — Slicing Aided Hyper Inference

Интеграция по [руководству Ultralytics SAHI](https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/).

- Инференс по срезам: большие изображения разбиваются на тайлы, детекция на каждом тайле, объединение результатов.
- Параметры: размер среза (height × width), коэффициенты перекрытия, порог уверенности.

**Зависимости:** `ultralytics`, `sahi` (`pip install sahi`).

Конфиг хранится в `integrations_config.json` (секция `sahi`).
