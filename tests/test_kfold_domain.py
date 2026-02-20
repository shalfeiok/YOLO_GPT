from app.features.kfold_integration.domain import KFoldConfig


def test_kfold_from_dict_parses_string_false_enabled() -> None:
    cfg = KFoldConfig.from_dict({"enabled": "false"})
    assert cfg.enabled is False


def test_kfold_from_dict_parses_string_true_enabled() -> None:
    cfg = KFoldConfig.from_dict({"enabled": "true"})
    assert cfg.enabled is True
