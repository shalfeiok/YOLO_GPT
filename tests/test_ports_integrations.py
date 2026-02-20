from __future__ import annotations


def test_container_integrations_port_smoke() -> None:
    """Smoke: container exposes integrations port and basic calls don't crash."""

    from app.application.container import Container

    c = Container()
    port = c.integrations
    assert port.export_formats

    # Should load persisted state (defaults exist in app_state) without raising.
    state = port.load_state()
    assert state is not None

    policy = port.load_jobs_policy()
    assert policy is not None
