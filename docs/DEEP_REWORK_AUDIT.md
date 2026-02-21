# YOLO_GPT — Deep Repo Dissection & Rework Plan

## Phase 1 — Repo Map

### Entry points
- `main.py::main()` bootstraps logging, Qt app, DI container, signals, main window, and error boundary wiring.
- UI composition starts from `app/ui/shell/main_window.py` and routes into `app/ui/views/*` screens.

### Main packages
- `app/ui/*`: presentation + Qt infra.
- `app/application/*`: use-cases, ports, facades, thin orchestration.
- `app/core/*`: event bus, jobs, errors, observability.
- `app/services/*`: imperative services bound to filesystem/model runtime.
- `app/features/*`: integration-specific domains/services/repositories.

### Runtime model
- Hybrid sync + background threads.
- UI on Qt main loop.
- Background processing via `ThreadPoolExecutor` (`JobRunner`).
- Synchronous in-process event dispatch via `EventBus.publish()`.

### Data flow (actual)
1. UI handler calls application facade/use-case.
2. Use-case schedules worker job via `JobRunner`.
3. `JobRunner` emits `Job*` events to `EventBus`.
4. `JobRegistry` receives events, mutates in-memory job state, optionally persists JSONL event history.
5. UI jobs view polls/reads registry records.

### Dependency hotspots
- `app/ui/infrastructure/di.py` and `app/application/container.py` act as hard coupling points.
- `app/application/ports/*` currently import `app.features.*.domain` types directly, reducing inversion.
- `app/ui/views/*` directly import facades/services in many places.

### Global state / singletons
- `EventBus`, `JobRunner`, `JobRegistry`, notifications are effectively app-wide service-locators via container.

### Hidden couplings
- Event name/type contracts between `JobRunner`, `JobRegistry`, and UI are implicit (no schema or contract tests).
- Dataset worker task ids (`prepare_yolo`, `augment`, etc.) are stringly typed and un-versioned.

---

## Phase 2 — Total Bug Hunt (top production blockers)

### Issue 1
- **File:** `app/core/jobs/job_runner.py`
- **Severity:** High
- **Type:** Logic / state consistency
- **Symptom:** Duplicate `JobCancelled` event may be emitted for a single cancellation path.
- **Root cause:** Cancellation was published in `_run_once()` and again in `_run()` cancellation branch.
- **Failure scenario:** Jobs UI receives two cancel events and may append duplicate logs/state transitions.
- **Minimal fix:** publish cancel event in one place only.
- **Proper fix:** explicit finite-state machine for job lifecycle transitions.
- **Regression test:** `tests/test_job_runner_cancellation_events.py` ensures exactly one cancellation event.

### Issue 2
- **File:** `app/core/jobs/job_registry.py`
- **Severity:** Critical
- **Type:** Race condition / state corruption
- **Symptom:** Concurrent event handling may corrupt in-memory `_jobs` map or produce inconsistent reads.
- **Root cause:** No locking around mutable registry state while events come from background threads.
- **Failure scenario:** Rapid progress/log events race with UI reads and purging, causing stale/missing records.
- **Minimal fix:** guard all mutable access with `RLock`.
- **Proper fix:** single-writer event-processing queue + immutable snapshots for UI.
- **Regression test:** existing suite + stress test to publish events concurrently.

### Issue 3
- **File:** `app/ui/views/datasets/worker.py::_run_prepare_yolo`
- **Severity:** High
- **Type:** Input validation / I/O safety
- **Symptom:** Empty output path (`""`) is interpreted as current directory (`Path('.')`).
- **Root cause:** validation used `if not out` after converting to `Path`; `Path('.')` is truthy.
- **Failure scenario:** dataset export is written into app CWD unexpectedly.
- **Minimal fix:** validate raw string before `Path()` conversion.
- **Proper fix:** centralized typed request DTO with strict validators.
- **Regression test:** `test_prepare_yolo_rejects_empty_output_for_non_voc`.

### Issue 4
- **File:** `app/ui/views/datasets/worker.py::_run_augment/_run_export_classes/_run_merge_classes`
- **Severity:** High
- **Type:** Input validation / data integrity
- **Symptom:** Same empty-output-path bug repeats in multiple operations.
- **Root cause:** duplicated validation pattern (`Path(...); if not out`).
- **Failure scenario:** writes into wrong directory, overwrites unrelated assets.
- **Minimal fix:** validate raw `out` string before path creation.
- **Proper fix:** one reusable validator for path-like user input across all tasks.
- **Regression test:** `test_augment_rejects_empty_output_path` + similar tests for export/merge.

### Issue 5
- **File:** `app/core/jobs/job_event_store.py`
- **Severity:** Medium
- **Type:** Observability / silent failure
- **Symptom:** all I/O errors are swallowed (`except Exception: return`), app never surfaces persistence failures.
- **Root cause:** fail-safe policy implemented without telemetry.
- **Failure scenario:** event history silently stops persisting after disk errors.
- **Minimal fix:** add warning logs in every swallowed exception branch.
- **Proper fix:** explicit persistence health state + surfaced notification.

### Issue 6
- **File:** `app/core/events/event_bus.py`
- **Severity:** Medium
- **Type:** Reliability
- **Symptom:** one handler exception aborts publish fan-out to remaining subscribers.
- **Root cause:** `publish()` calls handlers without per-handler isolation.
- **Failure scenario:** UI subscriber throws and blocks job registry update.
- **Minimal fix:** isolate handler failures with logging.
- **Proper fix:** supervised event dispatcher with dead-letter channel.

### Issue 7
- **File:** `app/core/jobs/job_runner.py`
- **Severity:** Medium
- **Type:** Resource leak risk
- **Symptom:** timed-out inner thread is daemonized and can continue running unbounded.
- **Root cause:** cooperative timeout can only request cancel; no enforced termination.
- **Failure scenario:** repeated hung jobs accumulate active daemon threads.
- **Minimal fix:** include watchdog metrics and caps; mark zombie count.
- **Proper fix:** process-based isolation for hard-killable risky jobs.

### Issue 8
- **File:** `main.py`
- **Severity:** Medium
- **Type:** Architecture / composition root leakage
- **Symptom:** bootstrapping code directly mutates container internals (`container.theme_manager = ...`).
- **Root cause:** mutable service locator without explicit constructor contracts.
- **Failure scenario:** initialization order bugs and hard-to-test side effects.
- **Minimal fix:** constructor-inject all dependencies into container once.
- **Proper fix:** explicit composition root module + frozen dependency graph.

---

### Issue 9
- **File:** `app/core/jobs/process_job_runner.py::_run_attempt`
- **Severity:** High
- **Type:** Runtime / state integrity
- **Symptom:** Supervisor can mark job as finished with `result=None` even when child process crashed before posting any terminal queue message.
- **Root cause:** `_run_attempt` returned `cast(T, result)` without verifying that a `"result"` message was actually received.
- **Failure scenario:** Child process exits early (spawn/import failure, abrupt interpreter exit) -> parent loop breaks on `not p.is_alive()` -> `error is None` and `result is None` -> false-positive success published to UI.
- **Minimal fix:** track `got_result` flag, use monotonic timeout accounting, drain queue briefly after child exit, close IPC queue deterministically, and raise runtime error when process exits without payload (including non-zero child exit code in the error).
- **Proper fix:** formal parent/child protocol with explicit terminal envelope and exit-code verification, plus crash-reason telemetry.
- **Regression test:** `tests/test_process_job_runner_exit_without_payload.py` ensures `JobFailed` is emitted when payload is missing and that late queue flush after child exit still produces `JobFinished`, and non-zero child exits without payload include exit-code diagnostics, while unknown and malformed child message envelopes (including invalid progress payload types and out-of-range progress values normalized to [0,1]) fail explicitly instead of being silently ignored, and queue cleanup still runs when child process startup itself fails.

## Phase 3 — Architectural Rework Plan

### Target architecture
1. **Domain layer**: pure models/rules (`app/domain/*`).
2. **Application layer**: use-cases + ports (`app/application/*`) depending only on domain + interfaces.
3. **Infrastructure layer**: filesystem, model backends, Qt adapters (`app/infrastructure/*`).
4. **Presentation layer**: Qt UI (`app/ui/*`) depends on application ports only.

### Import rules
- `ui -> application` ✅
- `application -> domain` ✅
- `infrastructure -> application/domain` ✅
- `domain -> (none)` ✅
- `application -> ui` ❌
- `domain -> infrastructure/ui` ❌

### Enforcement
- Add `import-linter` contracts for layer boundaries.
- Add architecture tests in `tests/architecture/test_imports.py`.
- Block merges in CI on contract violations.

### Migration strategy
- Strangler pattern by feature verticals:
  1. Jobs subsystem boundaries.
  2. Dataset operations.
  3. Integrations modules.
- Small PRs, each with adapter layer + parity tests.

---

## Phase 4 — Reliability Hardening
- Unified exception taxonomy with error codes.
- Structured logging (json) + correlation/job id.
- Timeout/retry policy config centralized.
- Crash bundle always includes recent job events and environment snapshot.
- Fail-fast for invariant violations; fail-safe only for non-critical persistence.

## Phase 5 — Performance Deep Check
- Baseline: `py-spy top` during training + `cProfile` for dataset operations.
- Memory: `tracemalloc` during long detection sessions.
- I/O: instrument event-store append latency and queue depth.
- Target metrics:
  - UI action-to-first-feedback < 100ms.
  - Job event publish p95 < 5ms.
  - No unbounded growth in thread count/log buffers.

## Phase 6 — Security Audit Plan
- Add secret scanning (`gitleaks`) in CI.
- Validate all user-provided paths with allowlisted roots.
- Pin + audit deps (`pip-audit`, `safety`).
- Harden subprocess/network integrations with explicit timeouts and TLS verification.

## Phase 7 — Test Strategy
1. **1–2 day safety net:** contracts around jobs, dataset worker validation, integration config IO.
2. Layered coverage targets by module criticality.
3. Contract tests for EventBus and JobEventStore formats.
4. Property tests for path sanitization + config migration idempotency.

## Phase 8 — DevEx & Release Hardening
- `pre-commit`: ruff, black, mypy, pytest-fast subset.
- CI matrix: lint + unit + architecture + security checks.
- Locked dependency sets + reproducible packaging.
- Conventional versioning + changelog automation.

## Phase 9 — Master Refactoring Backlog (excerpt)

| ID | Priority | Area | Description | Files | DoD | Size | Risk | Dependencies | PR Order |
|---|---|---|---|---|---|---|---|---|---|
| RB-01 | P0 | Jobs | Make job state transitions single-source-of-truth FSM | `app/core/jobs/*` | no duplicate transitions, full tests | M | Med | none | 1 |
| RB-02 | P0 | Concurrency | Single-writer registry pipeline | `app/core/jobs/job_registry.py` | race stress test passes | M | High | RB-01 | 2 |
| RB-03 | P0 | Dataset safety | Centralized path validator DTO | `app/ui/views/datasets/*`, `app/application/*` | invalid paths blocked, tests | S | Low | none | 3 |
| RB-04 | P1 | Architecture | Move feature domains into domain layer | `app/features/*`, `app/application/ports/*` | import-linter green | L | Med | RB-01 | 4 |
| RB-05 | P1 | Observability | Replace silent catches with structured telemetry | `app/core/*` | failures visible in logs/alerts | S | Low | none | 5 |
| RB-06 | P1 | CI Governance | Add import-linter + pip-audit gates | `.github/workflows/*`, `pyproject.toml` | CI blocks on violations | S | Low | none | 6 |
