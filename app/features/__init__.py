"""Feature modules (integrations).

IMPORTANT:
This package intentionally does *not* import any UI modules at import-time.

Why:
- Domain/service modules must be importable in headless environments (tests, CLI, CI)
- UI layers may depend on optional GUI toolkits (Qt/Tk) and should be imported lazily

UI registration is handled by the Qt shell (see app/ui) and/or an explicit registry module.
"""

from __future__ import annotations

__all__: list[str] = []
