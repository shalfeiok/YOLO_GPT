import pytest

pytest.importorskip("PySide6")

try:
    from app.ui.infrastructure.di import Container
    from app.ui.views.training_advisor.view import TrainingAdvisorView
except ImportError as exc:  # pragma: no cover - env-dependent
    pytest.skip(f"Qt UI unavailable: {exc}", allow_module_level=True)


def test_training_advisor_view_smoke(qtbot) -> None:
    container = Container()
    view = TrainingAdvisorView(container)
    qtbot.addWidget(view)
    assert view is not None
