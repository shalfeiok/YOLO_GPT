# Fix log

This file records runtime/compatibility fixes applied while executing the rework plan.

## 2026-02-20

- **Container.theme_manager / Container.notifications assignment compatibility**
  - Symptom: `AttributeError: property 'theme_manager' of 'Container' object has no setter`
  - Fix: Added property setters so both patterns work:
    - `container.theme_manager = theme_manager`
    - `container.set_theme_manager(theme_manager)`
    Same for `notifications`.

- **detection_visualization reset helper export**
  - Symptom: `ImportError: cannot import name 'reset_visualization_config_to_default' from 'app.features.detection_visualization'`
  - Fix: Implemented and exported `reset_visualization_config_to_default()` in `app/features/detection_visualization/__init__.py`
    (resets to `default_visualization_config()` and persists via `save_visualization_config()`).

- **Theme tokens import path compatibility**
  - Symptom: `ModuleNotFoundError: No module named 'app.ui.components.theme'`
  - Fix: Added shim module `app/ui/components/theme.py` that re-exports tokens/manager from `app.ui.theme`.
    This preserves old import paths while keeping the canonical implementation in `app/ui/theme/`.
