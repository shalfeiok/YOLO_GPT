from __future__ import annotations

import logging


def test_logging_setup_imports() -> None:
    # Import should be side-effect free and not require GUI.
    from app.core.observability.logging_config import setup_logging

    setup_logging(level="INFO")
    logging.getLogger(__name__).info("smoke")


def test_container_can_be_constructed_headless() -> None:
    # Container lives in the UI layer; it is OK to skip if PySide6 isn't installed
    # in a headless test environment.
    import pytest

    pytest.importorskip("PySide6")
    from app.ui.infrastructure.di import Container

    assert Container() is not None
