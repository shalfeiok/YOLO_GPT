# Установка

## Требования

- Python 3.10+ (рекомендуется 3.11).
- ОС: приоритетно Windows 10/11, но разработка возможна на Linux/macOS.
- Для обучения на GPU требуется совместимый стек PyTorch/CUDA.

## Установка зависимостей

### Вариант 1: runtime

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Вариант 2: для разработки

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

## Запуск

```bash
python main.py
```

## Где хранятся служебные данные

- jobs registry (jsonl), run manifests и логи пишутся в app state директорию (через `app/core/paths.py`).
