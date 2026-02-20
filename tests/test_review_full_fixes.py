from __future__ import annotations

from pathlib import Path

from app.application.facades import integrations as facade
from app.core.events import EventBus
from app.core.events.events import TrainingCancelled, TrainingFinished, TrainingProgress, TrainingStarted
from app.core.jobs import JobRegistry
from app.features.hyperparameter_tuning.domain import TuningConfig
from app.features.sahi_integration.domain import SahiConfig
from app.features.integrations_schema import IntegrationsConfig
from app.services.adapters.integrations_adapter import IntegrationsAdapter


def test_sahi_confidence_threshold_roundtrip() -> None:
    cfg = SahiConfig(confidence_threshold=0.77)
    data = cfg.to_dict()
    assert data["confidence_threshold"] == 0.77
    restored = SahiConfig.from_dict(data)
    assert restored.confidence_threshold == 0.77


def test_tuning_enabled_roundtrip() -> None:
    cfg = TuningConfig(enabled=True)
    data = cfg.to_dict()
    assert data["enabled"] is True
    restored = TuningConfig.from_dict(data)
    assert restored.enabled is True


def test_integrations_schema_reads_legacy_jobs_policy_key() -> None:
    raw = {"jobs_policy": {"retries": 3}}
    cfg = IntegrationsConfig.from_dict(raw)
    assert cfg.jobs.retries == 3


def test_integrations_adapter_loads_legacy_jobs_policy(monkeypatch) -> None:
    monkeypatch.setattr("app.services.adapters.integrations_adapter.load_config", lambda: {"jobs_policy": {"retries": 5}})
    adapter = IntegrationsAdapter()
    assert adapter.load_jobs_policy().retries == 5


def test_facade_save_jobs_policy_removes_legacy_key(monkeypatch) -> None:
    captured: dict = {}

    monkeypatch.setattr(facade, "load_integrations_config_dict", lambda: {"jobs_policy": {"retries": 1}})

    def _save(cfg: dict) -> None:
        captured.update(cfg)

    monkeypatch.setattr(facade, "save_integrations_config_dict", _save)
    facade.save_jobs_policy(facade.JobsPolicyConfig(retries=2))

    assert captured["jobs"]["retries"] == 2
    assert "jobs_policy" not in captured


def test_job_registry_tracks_training_events() -> None:
    bus = EventBus()
    reg = JobRegistry(bus)

    bus.publish(TrainingStarted(model_name="yolo11n.pt", epochs=10, project=Path("runs")))
    bus.publish(TrainingProgress(fraction=0.4, message="step"))
    jobs = reg.list()
    assert jobs
    assert jobs[0].name.startswith("Training:")
    assert jobs[0].progress == 0.4

    bus.publish(TrainingFinished(best_weights_path=None))
    assert reg.list()[0].status == "finished"


def test_job_registry_tracks_training_cancelled() -> None:
    bus = EventBus()
    reg = JobRegistry(bus)
    bus.publish(TrainingStarted(model_name="m", epochs=1, project=Path("runs")))
    bus.publish(TrainingCancelled(message="cancel"))
    assert reg.list()[0].status == "cancelled"


def test_job_registry_training_events_are_persisted() -> None:
    class _Store:
        def __init__(self) -> None:
            self.events = []

        def load(self):
            return []

        def append(self, event):
            self.events.append(event)

        def clear(self):
            self.events.clear()

    bus = EventBus()
    store = _Store()
    reg = JobRegistry(bus, store=store)

    bus.publish(TrainingStarted(model_name="yolo11n.pt", epochs=2, project=Path("runs")))
    bus.publish(TrainingProgress(fraction=0.5, message="mid"))
    bus.publish(TrainingFinished(best_weights_path=None))

    assert reg.list()[0].status == "finished"
    types = [e["type"] for e in store.events]
    assert "JobStarted" in types
    assert "JobProgress" in types
    assert "JobFinished" in types


def test_job_registry_training_ids_are_unique_for_quick_starts() -> None:
    bus = EventBus()
    reg = JobRegistry(bus)

    bus.publish(TrainingStarted(model_name="m1", epochs=1, project=Path("runs")))
    bus.publish(TrainingCancelled(message="stop"))
    bus.publish(TrainingStarted(model_name="m2", epochs=1, project=Path("runs")))

    job_ids = [j.job_id for j in reg.list()]
    assert len(job_ids) == 2
    assert len(set(job_ids)) == 2

