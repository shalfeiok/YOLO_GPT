from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any


def settings_diff(current: Any, updated: Any, prefix: str = "") -> list[dict[str, Any]]:
    """Return flat diff entries for dataclass/dict-like values."""

    left = _to_dict(current)
    right = _to_dict(updated)
    return _diff_dict(left, right, prefix=prefix)


def _to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"Unsupported value for diff: {type(value)!r}")


def _diff_dict(left: dict[str, Any], right: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in sorted(set(left) | set(right)):
        l_value = left.get(key)
        r_value = right.get(key)
        param = f"{prefix}.{key}" if prefix else key
        if isinstance(l_value, dict) and isinstance(r_value, dict):
            result.extend(_diff_dict(l_value, r_value, prefix=param))
            continue
        if l_value != r_value:
            result.append({"param": param, "current": l_value, "recommended": r_value})
    return result
