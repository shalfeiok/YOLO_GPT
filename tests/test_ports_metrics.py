from __future__ import annotations


def test_metrics_port_smoke():
    """Metrics port must be safe to call even when optional deps are missing."""

    from app.application.container import Container

    c = Container()
    cpu = c.metrics.get_cpu_percent()
    used_gb, total_gb = c.metrics.get_memory_info()
    gpu = c.metrics.get_gpu_info()

    assert isinstance(cpu, float)
    assert isinstance(used_gb, float)
    assert isinstance(total_gb, float)
    assert gpu is None or isinstance(gpu, dict)
