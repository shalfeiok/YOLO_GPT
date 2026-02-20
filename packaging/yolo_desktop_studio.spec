# PyInstaller spec for YOLO Desktop Studio.
#
# Build (Linux/macOS):
#   pyinstaller packaging/yolo_desktop_studio.spec
#
# Build (Windows):
#   pyinstaller packaging\\yolo_desktop_studio.spec

from __future__ import annotations

import os
from pathlib import Path

block_cipher = None

ROOT = Path(__file__).resolve().parents[1]


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v if v is not None else default


app_name = "yolo-desktop-studio"

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
