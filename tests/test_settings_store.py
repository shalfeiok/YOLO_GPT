from app.application.settings.store import AppSettingsStore


def test_store_update_reset_and_events() -> None:
    store = AppSettingsStore()
    events: list[str] = []
    store.subscribe("training_changed", lambda topic, payload: events.append(topic))

    updated = store.update_training(epochs=77)
    assert updated.epochs == 77
    assert store.get_snapshot().training.epochs == 77
    assert events == ["training_changed"]

    store.reset_to_defaults()
    assert store.get_snapshot().training.epochs != 77


def test_store_validation() -> None:
    store = AppSettingsStore()
    try:
        store.update_training(imgsz=10)
    except ValueError as exc:
        assert "imgsz" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
