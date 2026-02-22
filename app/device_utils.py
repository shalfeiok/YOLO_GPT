"""Device selection: prefer GPU; fall back to CPU only on runtime error (e.g. RTX 50xx sm_120)."""

from __future__ import annotations

# PyTorch 2.6 stable supports up to sm_90. RTX 5060 (sm_120) needs PyTorch nightly.
PYTORCH_NIGHTLY_HINT = "Для GPU на RTX 50xx: pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128"

# Full hint with network troubleshooting (getaddrinfo failed / no connection).
PYTORCH_NIGHTLY_HINT_FULL = """Для GPU на RTX 50xx нужен PyTorch nightly (cu128).

Установка (если есть доступ в интернет):
  pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128

Если ошибка getaddrinfo failed / нет соединения:
  1) Проверьте в браузере: открывается ли https://download.pytorch.org
  2) Попробуйте другой DNS (например 8.8.8.8) или VPN.
  3) Через Conda (если установлен): conda install pytorch -c pytorch-nightly
  4) Пока можно обучать на CPU — приложение переключится автоматически."""


def get_safe_device(requested: str = "") -> str:
    """
    Return device for inference only (detection). For training we try GPU first and fall back on error.
    If user explicitly chose CPU, return 'cpu'. Otherwise return '' (auto) so GPU is used when supported.
    """
    if requested and requested.strip().lower() == "cpu":
        return "cpu"
    return requested.strip() if requested else ""


def is_cuda_unsupported_capability() -> bool:
    """True if GPU is present but has capability not supported by this PyTorch (e.g. sm_120)."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        cap = torch.cuda.get_device_capability(0)
        # supported in stable 2.6: sm_50..sm_90
        return cap[0] > 9
    except Exception:
        return False
