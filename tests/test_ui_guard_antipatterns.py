import re
from pathlib import Path

PATTERNS = [
    re.compile(r"if\s+.*applying.*:\s*return\s+self\._settings\.update_"),
    re.compile(r"if\s+self\._is_applying_store_state\s*:\s*return\s+self\._settings\.update_"),
]


def test_no_guarded_update_antipattern_in_ui_views() -> None:
    root = Path("app/ui")
    offenders: list[str] = []
    for py_file in root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for pattern in PATTERNS:
            if pattern.search(text):
                offenders.append(f"{py_file}: {pattern.pattern}")
    assert not offenders, "\n".join(offenders)
