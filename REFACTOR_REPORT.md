# Refactor Report

## 1. Files Split

| Old file | Lines before | New modules created | Lines after |
|---|---:|---|---:|
| `app/core/jobs/process_job_runner.py` | 375 | `app/core/jobs/process_runner/{types.py,child_worker.py,log_buffer.py,runner.py,__init__.py}` + compatibility shim `process_job_runner.py` | 11 (shim) + 337 (new package) |
| `app/core/jobs/job_registry.py` | 333 | `app/core/jobs/job_registry_replay.py` (event replay extracted) | 216 + 69 |
| `app/services/yolo_prep_service.py` | 581 | `app/services/yolo_prep/{common.py,voc.py,prepare.py,class_ops.py,__init__.py}` + compatibility shim `yolo_prep_service.py` | 20 (shim) + 493 (package) |

## 2. Architectural Changes

- Jobs subsystem decomposed into dedicated modules for process orchestration, child IPC, log buffering and type contracts.
- Job registry replay logic extracted into a standalone replay module to isolate persistence replay from runtime state transitions.
- YOLO dataset preparation moved from a monolithic service into feature-focused modules:
  - shared parsing/constants (`common.py`),
  - VOC conversion (`voc.py`),
  - dataset discovery/split preparation (`prepare.py`),
  - class remapping operations (`class_ops.py`).
- Backward compatibility preserved via thin facade shims (`process_job_runner.py`, `yolo_prep_service.py`).

## 3. Dependency Improvements

- Reduced coupling between process lifecycle code and message parsing/log transport in jobs runner.
- Removed replay/persistence concerns from runtime `JobRegistry` event handlers.
- Separated dataset-IO concerns from class-remapping concerns in YOLO prep service to avoid mixed responsibilities.
- Preserved upstream imports through stable facade modules while introducing internal package boundaries.

## 4. Code Quality Improvements

- Improved readability by reducing cognitive load per module.
- Improved testability through smaller units (IPC child entry, log batching, replay logic, class-ops).
- Improved maintainability by minimizing risk of regressions during future changes to isolated submodules.
- Eliminated >300-line monolith in services layer (`yolo_prep_service.py`).

## 5. Future Scalability

- Jobs package now supports easier addition of new runner policies or transport adapters without modifying a single large file.
- Dataset preparation package now supports adding new dataset formats/export strategies without growing one monolithic service.
- Facade-based public API enables gradual internal evolution while keeping callers stable.
