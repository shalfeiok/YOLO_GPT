"""Tk-based UI (customtkinter) for this feature.

NOTE: The production app uses **PySide6**. This Tk UI has been moved to:
    examples/tk_ui/features/model_validation/ui.py

If you really need this UI, install optional dependency `customtkinter`
and run it from the examples folder.

Keeping this module as a stub avoids importing Tk dependencies in headless
environments (tests/CI) and keeps the product on a single GUI stack.
"""

from __future__ import annotations


def launch(*args, **kwargs):
    raise RuntimeError(
        "This feature UI is implemented as an optional Tk example and is not "
        "available in the production (PySide6) app. "
        "See examples/tk_ui/ for the original implementation."
    )
