# Packaging (PyInstaller)

This repo can be run from source:

```bash
python main.py
```

And it can be packaged into a standalone executable using **PyInstaller**.

## Build metadata (shown in the window title)

At build time, inject these environment variables:

- `YDS_VERSION` (e.g. `1.0.0`)
- `YDS_GIT_SHA` (short sha, e.g. `a1b2c3d`)
- `YDS_BUILD_DATE` (e.g. `2026-02-19`)

If not provided, the app shows `v0.0.0-dev (dev)`.

## Local build (recommended)

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt

export YDS_VERSION=0.1.0
export YDS_GIT_SHA=$(git rev-parse --short HEAD)
export YDS_BUILD_DATE=$(date +%F)

pyinstaller packaging/yolo_desktop_studio.spec
```

Artifacts will be in `dist/`.

## Notes

- On Linux you may need system packages for Qt (depends on the runner).
- Windows-only dependencies are guarded by platform markers in `requirements.txt`.
