from app.ui.common.guarded_update import GuardedStoreUpdate


class DummySettings:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def update_training(self, **changes) -> None:
        self.calls.append(changes)


def _guarded_update(guard: GuardedStoreUpdate, settings: DummySettings, **changes) -> None:
    if guard.should_ignore_user_change():
        return
    settings.update_training(**changes)


def test_guarded_update_skips_store_updates_while_applying() -> None:
    guard = GuardedStoreUpdate()
    settings = DummySettings()

    with guard.applying():
        _guarded_update(guard, settings, epochs=99)

    assert settings.calls == []


def test_guarded_update_updates_store_outside_apply_phase() -> None:
    guard = GuardedStoreUpdate()
    settings = DummySettings()

    _guarded_update(guard, settings, epochs=123, workers=8)

    assert settings.calls == [{"epochs": 123, "workers": 8}]
