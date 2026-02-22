"""Тесты доменных моделей интеграций Comet ML и DVC."""


from app.features.comet_integration.domain import CometConfig
from app.features.dvc_integration.domain import DVCConfig


class TestCometConfig:
    """from_dict / to_dict для Comet ML."""

    def test_from_dict_defaults(self) -> None:
        cfg = CometConfig.from_dict({})
        assert cfg.enabled is False
        assert cfg.api_key == ""
        assert cfg.project_name == "yolo26-project"
        assert cfg.max_image_predictions == 100
        assert cfg.eval_batch_logging_interval == 1
        assert cfg.eval_log_confusion_matrix is True
        assert cfg.mode == "online"

    def test_from_dict_partial(self) -> None:
        cfg = CometConfig.from_dict({"enabled": True, "project_name": "my-proj", "mode": "offline"})
        assert cfg.enabled is True
        assert cfg.project_name == "my-proj"
        assert cfg.mode == "offline"

    def test_to_dict_roundtrip(self) -> None:
        cfg = CometConfig(
            enabled=True,
            api_key="secret",
            project_name="p1",
            max_image_predictions=50,
            eval_batch_logging_interval=2,
            eval_log_confusion_matrix=False,
            mode="offline",
        )
        d = cfg.to_dict()
        restored = CometConfig.from_dict(d)
        assert restored.enabled == cfg.enabled
        assert restored.api_key == cfg.api_key
        assert restored.project_name == cfg.project_name
        assert restored.max_image_predictions == cfg.max_image_predictions
        assert restored.mode == cfg.mode


class TestDVCConfig:
    """from_dict / to_dict для DVC."""

    def test_from_dict_defaults(self) -> None:
        cfg = DVCConfig.from_dict({})
        assert cfg.enabled is False

    def test_from_dict_enabled(self) -> None:
        cfg = DVCConfig.from_dict({"enabled": True})
        assert cfg.enabled is True

    def test_to_dict_roundtrip(self) -> None:
        cfg = DVCConfig(enabled=True)
        d = cfg.to_dict()
        assert d == {"enabled": True}
        restored = DVCConfig.from_dict(d)
        assert restored.enabled == cfg.enabled
