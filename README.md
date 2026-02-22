# YOLO_GPT

## What is YOLO_GPT
YOLO_GPT is a desktop application for training and running YOLO-based computer vision workflows. It provides a Qt UI around dataset preparation, training, detection, and job tracking. The project is structured to keep UI, application services, and core domain components separated.

## Features
- YOLO model training workflows from the desktop UI.
- Detection/inference flows for image or stream-like scenarios.
- Dataset tooling (preparation, augmentation, and visualization helpers).
- Background jobs and run tracking for long operations.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

## Dev setup
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
ruff check . --fix
ruff format .
black .
pytest
pytest -q
pre-commit install
pre-commit run -a
```

## Torch/CUDA note
Install `torch`/`torchvision`/`torchaudio` separately for your target CUDA/CPU environment before running heavy training workloads.

## Logs & runs
Runtime logs and run artifacts are written under project runtime directories (for example `runs/` and related output folders created by training/detection jobs).
