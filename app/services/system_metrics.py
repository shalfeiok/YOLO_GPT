"""System metrics: CPU, RAM, GPU (NVIDIA) for UI display."""
from __future__ import annotations

from typing import Any, Optional


def get_cpu_percent() -> float:
    """CPU usage 0-100."""
    try:
        import psutil
        return psutil.cpu_percent(interval=None) or 0.0
    except Exception:
        return 0.0


def get_memory_info() -> tuple[float, float]:
    """Return (used_gb, total_gb)."""
    try:
        import psutil
        v = psutil.virtual_memory()
        return (v.used / (1024 ** 3), v.total / (1024 ** 3))
    except Exception:
        return (0.0, 0.0)


def get_gpu_info() -> Optional[dict[str, Any]]:
    """GPU util %, memory used/total MB, temperature if available. None if no NVIDIA.
    Prefer pip install nvidia-ml-py (replaces deprecated pynvml) to avoid FutureWarning.
    """
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import pynvml
    except ImportError:
        try:
            import subprocess
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split("\n")[0].split(", ")
                if len(parts) >= 3:
                    return {
                        "util": float(parts[0].strip().split()[0]) if parts[0].strip() else 0,
                        "mem_used_mb": float(parts[1].strip().split()[0]) if parts[1].strip() else 0,
                        "mem_total_mb": float(parts[2].strip().split()[0]) if parts[2].strip() else 0,
                        "temp": float(parts[3].strip().split()[0]) if len(parts) > 3 and parts[3].strip() else None,
                    }
        except Exception:
            import logging
            logging.getLogger(__name__).debug('System metrics collection failed', exc_info=True)
        return None
    try:
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(h)
        mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        try:
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        except Exception:
            temp = None
        pynvml.nvmlShutdown()
        return {
            "util": util.gpu,
            "mem_used_mb": mem.used / (1024 ** 2),
            "mem_total_mb": mem.total / (1024 ** 2),
            "temp": temp,
        }
    except Exception:
        return None
