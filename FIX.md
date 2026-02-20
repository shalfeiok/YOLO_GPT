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

## Hotfix 2026-02-20 (runtime)
- Fix: `TrainingView` crash: add missing import `SecondaryButton` in `app/ui/views/training/sections.py`.
- Fix: `IntegrationsView` crash: add `enabled: bool` to `KFoldConfig` models (`app/features/integrations_schema.py`, `app/features/kfold_integration/domain.py`) and parse/serialize it.
- Fix: `DetectionView` stop crash: initialize and lazy-create `Container._stop_detection_uc` and `stop_detection_use_case`.


## Hotfix 2026-02-20 (runtime follow-up)
- Fixed NameError: `SecondaryButton`/`PrimaryButton`/`NoWheelSpinBox` missing imports in `app/ui/views/training/sections.py`.
- Fixed NameError in `KFoldConfig.from_dict`: used undefined `m` variable; corrected to `d` in `app/features/kfold_integration/domain.py`.
- Added `enabled` field parsing/serialization to schema `KFoldConfig` in `app/features/integrations_schema.py` for consistency.

## Hotfix 2026-02-20 - runtime (training/integrations)
- Fixed NameError: missing `import os` in `app/ui/views/training/sections.py`.
- Fixed KFoldConfig.from_dict bug (`m` -> `d`) and added alias property `k` -> `k_folds`.
- Updated Integrations KFold UI to use `k_folds` (backward compatible) and preserve full config via `replace(cfg, ...)`.

## Hotfix 2026-02-20 - startup crash (IndentationError)
- Fixed syntax/indentation error in `app/features/integrations_schema.py` (`KFoldConfig.from_dict` had extra parenthesis and wrong indentation).


## Hotfix 2026-02-20 (runtime stability 2)
- Training: added missing imports `os` and `PROJECT_ROOT` in `app/ui/views/training/sections.py`.
- Integrations: added `enabled` support to `TuningConfig` (schema + domain) and safe parsing default.
- Integrations: fixed `KFoldConfig.from_dict` NameError (`m` -> `d`).
- Jobs: added empty-state label when no jobs are present.
