import logging

from app.services.training_service import _split_advanced_options


def test_split_advanced_options_applies_whitelist_and_reports_dropped(caplog) -> None:
    options = {
        "cache": True,
        "mixup": 0.2,
        "close_mosaic": 8,
        "run_profile": "fast",
        "unknown_flag": 123,
    }

    applied, dropped = _split_advanced_options(options)

    assert applied == {"cache": True, "mixup": 0.2, "close_mosaic": 8}
    assert dropped == ["run_profile", "unknown_flag"]

    caplog.set_level(logging.INFO)
    logging.getLogger("app.services.training_service").info(
        "Starting YOLO training with args=%s advanced_applied=%s advanced_dropped=%s",
        {"epochs": 5},
        applied,
        dropped,
    )
    assert "advanced_applied" in caplog.text
    assert "advanced_dropped" in caplog.text
