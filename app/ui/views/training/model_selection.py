from __future__ import annotations

from pathlib import Path
from typing import Iterable

CUSTOM_MODEL_CHOICE = "Наша модель (файл…)…"


def _normalize_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def resolve_model_choice_label(
    *,
    model_name: str,
    weights_path: str | None,
    trained_choices: Iterable[tuple[str, Path]],
    base_choices: Iterable[tuple[str, str]],
) -> str | None:
    """Resolve combo label that should represent current training settings."""
    if weights_path:
        selected = _normalize_path(weights_path)
        for label, path in trained_choices:
            if _normalize_path(path) == selected:
                return label
        return CUSTOM_MODEL_CHOICE

    for label, candidate_model_name in base_choices:
        if candidate_model_name == model_name:
            return label
    return None
