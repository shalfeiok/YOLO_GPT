from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.application.ports.integrations import IntegrationsPort, JobsPolicyConfig


class JobsPolicyDialog(QDialog):
    """Edit default retry/timeout policy for background jobs."""

    def __init__(self, parent=None, *, integrations: IntegrationsPort | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Политика задач")
        self.setMinimumWidth(420)

        # Prefer injected port (UI boundary), fallback to legacy facade for compatibility.
        self._integrations = integrations
        if self._integrations is not None:
            policy = self._integrations.load_jobs_policy()
        else:  # pragma: no cover
            from app.application.facades.integrations import load_jobs_policy as _load

            policy = _load()

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Настройте дефолтные timeout/retry для фоновых задач."))

        form = QFormLayout()

        self._timeout = QSpinBox()
        self._timeout.setRange(0, 24 * 60 * 60)
        self._timeout.setValue(int(policy.default_timeout_sec))
        self._timeout.setSuffix(" сек")
        form.addRow("Timeout по умолчанию", self._timeout)

        self._retries = QSpinBox()
        self._retries.setRange(0, 20)
        self._retries.setValue(int(policy.retries))
        form.addRow("Retries", self._retries)

        self._backoff = QDoubleSpinBox()
        self._backoff.setRange(0.0, 3600.0)
        self._backoff.setDecimals(2)
        self._backoff.setValue(float(policy.retry_backoff_sec))
        self._backoff.setSuffix(" сек")
        form.addRow("Backoff base", self._backoff)

        self._jitter = QDoubleSpinBox()
        self._jitter.setRange(0.0, 1.0)
        self._jitter.setDecimals(2)
        self._jitter.setValue(float(policy.retry_jitter))
        form.addRow("Jitter (0..1)", self._jitter)

        self._deadline = QSpinBox()
        self._deadline.setRange(0, 24 * 60 * 60)
        self._deadline.setValue(int(policy.retry_deadline_sec))
        self._deadline.setSuffix(" сек")
        form.addRow("Retry deadline (0=нет)", self._deadline)

        root.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.clicked.connect(self._on_save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

    def _on_save(self) -> None:
        policy = JobsPolicyConfig(
            default_timeout_sec=int(self._timeout.value()),
            retries=int(self._retries.value()),
            retry_backoff_sec=float(self._backoff.value()),
            retry_jitter=float(self._jitter.value()),
            retry_deadline_sec=int(self._deadline.value()),
        )
        if self._integrations is not None:
            self._integrations.save_jobs_policy(policy)
        else:  # pragma: no cover
            from app.application.facades.integrations import save_jobs_policy as _save

            _save(policy)
        self.accept()
