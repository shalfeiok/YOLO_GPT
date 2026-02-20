from __future__ import annotations

from pathlib import Path

from app.application.facades import integrations as facade
from app.core.events import EventBus
from app.core.events.job_events import JobStarted
from app.core.events.events import TrainingCancelled, TrainingFinished, TrainingProgress, TrainingStarted
from app.core.jobs import JobRegistry
from app.features.hyperparameter_tuning.domain import TuningConfig
from app.features.sahi_integration.domain import SahiConfig
from app.features.integrations_schema import IntegrationsConfig, KFoldConfig
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


def test_kfold_enabled_parses_string_false_as_false() -> None:
    cfg = KFoldConfig.from_dict({"enabled": "false"})
    assert cfg.enabled is False


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

def test_job_registry_supersedes_previous_running_training() -> None:
    bus = EventBus()
    reg = JobRegistry(bus)

    bus.publish(TrainingStarted(model_name="m1", epochs=5, project=Path("runs")))
    first_id = reg.list()[0].job_id
    bus.publish(TrainingStarted(model_name="m2", epochs=3, project=Path("runs")))

    first = reg.get(first_id)
    assert first is not None
    assert first.status == "cancelled"
    assert first.message == "superseded by a new training run"

    jobs = reg.list()
    assert jobs[0].name == "Training: m2"
    assert jobs[0].status == "running"

def test_job_registry_persists_training_cancel_reason_message() -> None:
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

    bus.publish(TrainingStarted(model_name="m", epochs=1, project=Path("runs")))
    bus.publish(TrainingProgress(fraction=0.25, message="warmup"))
    bus.publish(TrainingCancelled(message="user stop"))

    assert reg.list()[0].status == "cancelled"
    progress_messages = [e["data"].get("message") for e in store.events if e["type"] == "JobProgress"]
    assert "user stop" in progress_messages

def test_job_registry_replay_restores_cancel_message_and_tolerates_missing_name() -> None:
    class _Store:
        def load(self):
            return [
                {
                    "type": "JobStarted",
                    "data": {"job_id": "j1", "name": "Replay Train"},
                },
                {
                    "type": "JobProgress",
                    "data": {"job_id": "j1", "progress": 0.4, "message": "user stop"},
                },
                {
                    "type": "JobCancelled",
                    "data": {"job_id": "j1"},
                },
            ]

        def append(self, event):
            pass

        def clear(self):
            pass

    bus = EventBus()
    reg = JobRegistry(bus, store=_Store(), replay_on_start=True)

    rec = reg.get("j1")
    assert rec is not None
    assert rec.status == "cancelled"
    assert rec.message == "user stop"
    assert rec.name == "Replay Train"

def test_job_registry_replay_does_not_reappend_events() -> None:
    class _Store:
        def __init__(self) -> None:
            self.append_calls = 0

        def load(self):
            return [
                {"type": "JobStarted", "data": {"job_id": "j1", "name": "Task"}},
                {"type": "JobProgress", "data": {"job_id": "j1", "name": "Task", "progress": 0.2, "message": "ok"}},
            ]

        def append(self, event):
            self.append_calls += 1

        def clear(self):
            pass

    store = _Store()
    reg = JobRegistry(EventBus(), store=store, replay_on_start=True)

    assert reg.get("j1") is not None
    assert store.append_calls == 0

def test_job_registry_live_events_during_replay_are_persisted() -> None:
    bus = EventBus()

    class _Store:
        def __init__(self) -> None:
            self.events = []
            self.sent_live = False

        def load(self):
            if not self.sent_live:
                self.sent_live = True
                bus.publish(JobStarted(job_id="live-1", name="Live During Replay"))
            return []

        def append(self, event):
            self.events.append(event)

        def clear(self):
            self.events.clear()

    store = _Store()
    reg = JobRegistry(bus, store=store, replay_on_start=True)

    assert reg.get("live-1") is not None
    assert any(e.get("type") == "JobStarted" and e.get("data", {}).get("job_id") == "live-1" for e in store.events)

def test_job_registry_replay_load_exception_is_safe() -> None:
    class _Store:
        def load(self):
            raise RuntimeError("boom")

        def append(self, event):
            raise AssertionError("append should not be called")

        def clear(self):
            pass

    reg = JobRegistry(EventBus(), store=_Store(), replay_on_start=True)
    assert reg.list() == []


def test_job_registry_replay_ignores_non_dict_records() -> None:
    class _Store:
        def load(self):
            return [None, "oops", 42, {"type": "JobStarted", "data": {"job_id": "j", "name": "ok"}}]

        def append(self, event):
            raise AssertionError("append should not be called during replay")

        def clear(self):
            pass

    reg = JobRegistry(EventBus(), store=_Store(), replay_on_start=True)
    rec = reg.get("j")
    assert rec is not None
    assert rec.name == "ok"

def test_job_registry_replay_non_list_payload_is_safe() -> None:
    class _Store:
        def load(self):
            return None

        def append(self, event):
            raise AssertionError("append should not be called")

        def clear(self):
            pass

    reg = JobRegistry(EventBus(), store=_Store(), replay_on_start=True)
    assert reg.list() == []
