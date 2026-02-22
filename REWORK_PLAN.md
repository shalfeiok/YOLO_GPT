# Rework Plan

## Rules
- 1 commit = 1 atomic task.
- In every commit: mark completed task with ✅ and append changelog line `YYYY-MM-DD — <short_sha> — <summary>`.
- Priorities: Crash → Freeze → Data-loss → Perf → UX → Cleanliness.
- Any risky behavior change must include guardrails and tests/self-checks.

## Backlog
- [x] ✅ Task 0 — Full audit and normalize this rework plan format.
- [x] ✅ Task A0 — Fix application container crash in ProcessJobRunner wiring.
- [ ] Task A1 — Crash-safe tabs: ensure StackController error boundary has UI fallback, traceback actions, and coverage.
- [x] ✅ Task B1 — Batch/throttle job logs in runners and UI pipeline to reduce event spam.
- [ ] Task C1 — Make training execution use ProcessJobRunner by default with cancel/timeout mapping.
- [ ] Task C2 — Harden IPC payload validation/tests for process runner progress/log message contract.
- [ ] Task D1 — Wire TrainingRunSpec profile selection end-to-end and persist manifest spec from resolved run spec.
- [x] ✅ Task D2 — Jobs UI artifacts links (run folder, weights, plots, manifest).
- [x] ✅ Task E1 — Remove UI-only dependencies from application container; keep UI composition in UI layer.
- [x] ✅ Task F0 — Fix Python 3.10 compatibility in run manifest timestamps.
- [ ] Task F1 — Tooling/docs sanity pass (README/requirements/pre-commit/pyproject) and close gaps for Windows predictability.
- [ ] Task F2 — Expand smoke tests for core contracts (EventBus, JobRegistry, ProcessJobRunner) without ML/Qt deps.
- [ ] Task F3 — CI workflow check (lint + tests) stable on GitHub Actions.

## Audit Backlog Details
### A) Crash points
- `app/application/container.py`: `process_job_runner` passes unsupported `event_store` kwarg to `ProcessJobRunner`, causing runtime crash once accessed.
- `app/ui/views/training/view_model.py`: training worker exceptions can race with queue finalization and leak inconsistent state.

### B) UI freeze points
- `TrainingViewModel.start_training` uses dedicated non-daemon thread + synchronous trainer; heavy training lifecycle still managed from VM and can backlog UI signals.
- `JobRunner` and `ProcessJobRunner` publish log events per line causing event-bus amplification during verbose runs.

### C) Performance bottlenecks
- Per-line event publish for stdout/stderr in both runners.
- Jobs view refreshes full table for bursts of events; debounced but still receives excess events.

### D) Reliability gaps
- Training path is not consistently executed via process runner default path.
- Manifest spec in training VM is currently built from raw request values, not normalized `TrainingRunSpec` profile result.

### E) Testing/documentation/tooling gaps
- No targeted tests for batched log flushing behavior.
- Need explicit test around tab-factory error boundary UX fallback.

## Done
- ✅ Task 0 — Full audit and normalize this rework plan format.
- ✅ Task A0 — Fix application container crash in ProcessJobRunner wiring.
- ✅ Task B1 — Batch/throttle job logs in runners and UI pipeline to reduce event spam.
- ✅ Task D2 — Jobs UI artifacts links (run folder, weights, plots, manifest).
- ✅ Task E1 — Remove UI-only dependencies from application container; keep UI composition in UI layer.
- ✅ Task F0 — Fix Python 3.10 compatibility in run manifest timestamps.

## Changelog
- 2026-02-22 — pending — chore(plan): audit and rebuild REWORK_PLAN backlog

- 2026-02-22 — pending — fix(container): remove invalid ProcessJobRunner kwargs
- 2026-02-22 — pending — perf(jobs): batch log events in thread/process runners
- 2026-02-22 — pending — feat(jobs): add artifact shortcuts for manifest/weights/plots
- 2026-02-22 — pending — refactor(di): move UI-only deps to ui container shim
- 2026-02-22 — pending — fix(observability): use timezone.utc for py310 compatibility
- 2026-02-22 — pending — fix(logging): replace datetime.UTC for py310 compatibility
- 2026-02-22 — pending — style: format touched files with ruff format
- 2026-02-22 — pending — fix(lint): resolve ruff issues in touched files
