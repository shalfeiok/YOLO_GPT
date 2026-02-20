# Разработка

## Запуск тестов

```bash
pip install -r requirements-dev.txt
pytest
# или с подробным выводом:
pytest -v
# только один файл:
pytest tests/test_training_metrics.py -v
```

Конфигурация pytest задаётся в `pytest.ini` (каталог `tests/`, префикс `test_*.py`).

## Стиль кода

- **PEP 8**: отступы 4 пробела, длина строки до 100–120 символов по возможности.
- **Типизация**: для публичных функций и методов указывать аннотации типов (`typing`).
- **Docstrings**: в формате Google (Args, Returns, Raises) для модулей, классов и публичных методов.

## Добавление новой интеграции

1. Создайте каталог в `app/features/`, например `app/features/new_integration/`.
2. Добавьте модули:
   - `domain.py` — датаклассы/модели конфига с `from_dict` / `to_dict`.
   - `service.py` — бизнес-логика (вызов внешних API, env, subprocess).
   - `repository.py` — чтение/запись секции через `app.features.integrations_config` (load_config, save_config).
   - `ui.py` — функция `build_<name>_section(parent, on_reset_defaults)` возвращает `CTkFrame`.
   - `README.md` — краткое описание и ссылка на документацию.
3. В `app/features/integrations_config.py` добавьте секцию в `default_config()` и при необходимости в `load_config` (merge).
4. В `app/features/__init__.py` экспортируйте `build_<name>_section`.
5. В `app/ui/integrations_tab.py` вызовите `build_<name>_section(scroll, noop)` и разместите фрейм в `scroll` (например, следующая строка grid).
6. Если интеграция должна влиять на обучение — в `app/services/training_service.py` в начале потока `run()` загрузите конфиг и примените настройки (env, аргументы `model.train()`).

Главное окно не должен знать о внутренней логике модуля: только импорт виджета и вставка во вкладку.

## Структура тестов

- `tests/test_*.py` — модульные тесты для парсеров, конфигов, доменных моделей, хелперов.
- Используйте `tmp_path` (pytest fixture) для временных файлов и каталогов, чтобы не трогать реальный проект.
- Для тестов конфига интеграций передавайте `path=tmp_path / "config.json"`, чтобы не перезаписывать `integrations_config.json` в корне.
- Домены гайдов (J–M): `tests/test_guides_domains.py` — ModelValidationConfig, SegIsolationConfig, SolutionsConfig; наличие секций в конфиге — `tests/test_integrations_config.py` (test_has_guides_sections).

## Модули гайдов (секции J–M)

- **segmentation_isolation** — изоляция объектов по маскам сегментации (YOLO seg), сохранение PNG с чёрным или прозрачным фоном.
- **model_validation** — запуск `model.val(data=...)`, вывод mAP50, mAP50–95, precision, recall.
- **ultralytics_solutions** — генерация и запуск в subprocess скрипта с `ultralytics.solutions` (DistanceCalculation, Heatmap, ObjectCounter, RegionCounter, SpeedEstimator, TrackZone).
- **guides_launchers** — только UI: запуск Streamlit inference, сохранение шаблона Custom Trainer.

Подробнее: [Гайды Ultralytics (J–M)](guides.md).
