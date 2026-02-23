# YOLO Desktop Studio

> Desktop-приложение на Python/PySide6 для практической работы с YOLO: подготовка датасета, обучение, рекомендации по тюнингу, детекция, валидация, мониторинг задач и интеграции.

## О проекте

### Коротко
YOLO Desktop Studio — это UI-оболочка и прикладной слой для типового CV workflow: **Dataset → Train → Advisor → Detect/Validate → Analyze artifacts**.

### Развернуто
Проект разделён на слои:
- `app/ui` — экранные формы, shell, виджеты, view model;
- `app/application` — use-case, DI-контейнер, settings store, порты;
- `app/core` — job/event инфраструктура, observability, training advisor ядро;
- `app/services` — реализация тренировки/детекции и адаптеры.

Подробная документация: [docs/index.md](docs/index.md).

## Возможности (по вкладкам)

- **Datasets**: работа с датасетом и подготовкой данных.
- **Training**: запуск обучения Ultralytics YOLO с базовыми и advanced параметрами.
- **Training Advisor**: анализ датасета/артефактов и рекомендации + Apply/Undo.
- **Detection**: запуск инференса (PyTorch/ONNX).
- **Validation**: проверка качества модели на dataset yaml.
- **Integrations**: настройки интеграций и конфигов.
- **Jobs**: мониторинг задач, логи, retry/cancel, доступ к артефактам.
- Дополнительные вкладки (segmentation, pose, tracking и т.д.) доступны в shell и могут быть частично placeholder в текущей фазе.

## Скриншоты

Плейсхолдеры (добавьте реальные скриншоты после запуска приложения):
- `docs/assets/training.png` — экран обучения
- `docs/assets/advisor.png` — экран советника
- `docs/assets/jobs.png` — мониторинг задач

Как добавить:
1. Сделайте скриншот окна приложения.
2. Сохраните в `docs/assets/`.
3. Вставьте в README markdown-ссылкой.

## Требования

- Python 3.10+ (рекомендуется 3.11)
- Для GPU: совместимые `torch`/CUDA/driver
- ОС: Windows 10/11 приоритетно, Linux/macOS для разработки поддерживаются

## Установка

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Для разработки:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

## Запуск приложения

```bash
python main.py
```

## Быстрый старт

1. Запустите приложение.
2. Проверьте датасет (структура + `data.yaml`).
3. На вкладке Training задайте модель/параметры и стартуйте обучение.
4. После прогона используйте Training Advisor и примените рекомендации.
5. Выполните Detection/Validation и посмотрите артефакты/логи через Jobs.

Подробно: [docs/quickstart.md](docs/quickstart.md).

## Как обучить модель (детально)

1. Подготовьте датасет в YOLO-формате: [docs/datasets/format.md](docs/datasets/format.md).
2. На вкладке Training:
   - `model_name` (напр. `yolo11n.pt`),
   - `weights_path` (опционально),
   - `epochs/batch/imgsz/patience/workers/optimizer`.
3. При необходимости откройте advanced настройки: [docs/training/advanced.md](docs/training/advanced.md).
4. Запустите обучение.
5. Смотрите `runs/train/*`: [docs/training/artifacts.md](docs/training/artifacts.md).

## Советник по обучению: как использовать и применять рекомендации

1. Откройте вкладку Training Advisor.
2. Передайте путь к весам, датасету и (опционально) run folder.
3. Запустите анализ (Quick/Deep).
4. Просмотрите diff параметров.
5. Нажмите Apply для записи в settings store.
6. При необходимости Undo.

Подробно: [docs/ui/training_advisor.md](docs/ui/training_advisor.md).

## Детекция / Валидация / Интеграции / Задачи

- Детекция: [docs/detection/inference.md](docs/detection/inference.md)
- Валидация: [docs/validation/metrics.md](docs/validation/metrics.md)
- Интеграции: [docs/integrations/overview.md](docs/integrations/overview.md)
- Задачи и логи: [docs/jobs/queue_and_logs.md](docs/jobs/queue_and_logs.md)

## Структура датасета

```text
dataset/
  data.yaml
  images/train
  images/val
  labels/train
  labels/val
```

Пример:

```yaml
train: images/train
val: images/val
names: [class0, class1]
```

## Структура runs/артефактов

```text
runs/train/exp*/
  results.csv
  args.yaml
  weights/best.pt
  weights/last.pt
  events.out.tfevents...
```

## Разработка

- Архитектура: [docs/architecture/layers.md](docs/architecture/layers.md)
- DI: [docs/architecture/di_container.md](docs/architecture/di_container.md)
- Events/Jobs/Store: [docs/architecture/events_jobs_store.md](docs/architecture/events_jobs_store.md)

### Как добавить новую вкладку
1. Создайте view в `app/ui/views/<feature>/view.py`.
2. Добавьте фабрику в `MainWindow`/`StackController`.
3. При необходимости подключите use-case через `Container`.

### Как добавить новый use-case
1. Создайте класс в `app/application/use_cases`.
2. Определите/используйте порт в `app/application/ports`.
3. Зарегистрируйте в `Container`.
4. Добавьте unit/integration тесты.

## Тестирование

Единая команда:

```bash
pytest -q
```

Дополнительно (опционально):

```bash
ruff check .
ruff format .
```

- Тесты организованы по папкам `tests/unit`, `tests/integration`, `tests/ui_smoke` + исторические тесты в `tests/`.
- Отчёт: [TEST_REPORT.md](TEST_REPORT.md).

## Troubleshooting

Кратко:
- проверьте пути `data.yaml` и split folders;
- проверьте CUDA/torch/driver совместимость;
- исправьте аннотации (bbox range, class id).

Подробно: [docs/troubleshooting.md](docs/troubleshooting.md).

## Вклад и лицензия

- Вклад приветствуется через PR.
- Смотрите текущие файлы лицензии/политики репозитория (если присутствуют).
