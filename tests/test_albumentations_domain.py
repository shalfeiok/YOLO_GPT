"""Тесты доменных моделей интеграции Albumentations."""
import pytest

from app.features.albumentations_integration.domain import (
    AlbumentationsConfig,
    STANDARD_TRANSFORM_NAMES,
)


class TestAlbumentationsConfig:
    """from_dict / to_dict."""

    def test_from_dict_defaults(self) -> None:
        cfg = AlbumentationsConfig.from_dict({})
        assert cfg.enabled is False
        assert cfg.use_standard is True
        assert cfg.custom_transforms == []
        assert cfg.transform_p == 0.5

    def test_from_dict_partial(self) -> None:
        cfg = AlbumentationsConfig.from_dict({"enabled": True, "transform_p": 0.8})
        assert cfg.enabled is True
        assert cfg.transform_p == 0.8

    def test_to_dict_roundtrip(self) -> None:
        cfg = AlbumentationsConfig(
            enabled=True,
            use_standard=False,
            custom_transforms=[{"name": "Blur", "p": 0.3}],
            transform_p=0.6,
        )
        d = cfg.to_dict()
        restored = AlbumentationsConfig.from_dict(d)
        assert restored.enabled == cfg.enabled
        assert restored.use_standard == cfg.use_standard
        assert len(restored.custom_transforms) == 1
        assert restored.custom_transforms[0]["name"] == "Blur"
        assert restored.transform_p == cfg.transform_p


class TestStandardTransformNames:
    """Константа STANDARD_TRANSFORM_NAMES."""

    def test_contains_expected(self) -> None:
        assert "Blur" in STANDARD_TRANSFORM_NAMES
        assert "CLAHE" in STANDARD_TRANSFORM_NAMES
        assert "GaussNoise" in STANDARD_TRANSFORM_NAMES
