# Architecture

## Layers

**UI (PySide6)**
- `app/ui/...`
- Views and ViewModels.
- No business logic beyond input validation and state mapping.

**Application (Use Cases)**
- `app/application/use_cases/...`
- Orchestrates services and domain logic to fulfill a user intent.
- Stable API for the UI.

**Services / Infrastructure**
- `app/services/...`
- Adapters over external libraries (Ultralytics, ONNX, etc.) and OS resources.

**Domain**
- `app/domain/...`
- Pure business rules and entities.

## Direction of Dependencies

UI → Application (use cases) → Services/Repositories → Domain

Rule: UI should not import feature-level service modules directly.

## Training Flow

1. `TrainingViewModel` starts a single worker thread.
2. Worker calls `TrainModelUseCase.execute()`.
3. Use case calls the trainer service synchronously and streams progress via callbacks.
4. Console output is polled from a queue and emitted to UI via Qt signals.

## Events (decoupling)

Use-cases can publish application events via `app/core/events/EventBus`.
UI can subscribe and re-dispatch to the Qt main thread when needed.

Training publishes:
- `TrainingStarted`
- `TrainingProgress`
- `TrainingFinished`
- `TrainingCancelled`
- `TrainingFailed`


## Tk-based feature UIs

Some feature folders previously included `customtkinter` UIs (`app/features/*/ui.py`).
The production application uses **PySide6** only, so those Tk UIs were moved to `examples/tk_ui/`.
The in-package `ui.py` files are now stubs that raise a clear error if called, preventing optional GUI dependencies from breaking tests/CI.
