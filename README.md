# YOLO_GPT

## Overview
YOLO_GPT is a desktop application for training and running YOLO-based computer-vision workflows.
The codebase is split into UI (`app/ui`), application/use-cases (`app/application`), and core infra (`app/core`).

## Requirements
- Python 3.10+ (recommended: 3.11)
- OS: Windows 10/11 is the primary target (Linux/macOS also supported for development)

## Runtime install
> Install PyTorch separately for your CPU/CUDA environment before heavy training.

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

### Linux/macOS
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Development setup
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

## Quality checks
```bash
python -m compileall .
ruff check .
ruff format .
pytest -q
pre-commit run -a
```

## Dependencies split
- `requirements.txt` — runtime dependencies only.
- `requirements-dev.txt` — development tooling (ruff, black, pytest, pre-commit, mypy, etc.).

## Logs and run artifacts
Runtime logs and run manifests are written under app state/run folders and surfaced in the Jobs UI.
