# Progress Tracker

## Plan (grouped commits)
- [x] Group 1: StackController error boundary (safe tab failures)
- [x] Group 2: Lazy first-open tab creation without UI freeze
- [x] Group 3: Jobs visibility for dataset/training/detection actions
- [x] Group 4: Throttling/batching to reduce UI spam
- [x] Group 5: TrainingRunSpec + reproducible profiles
- [x] Group 6: Run manifests + open run folder from Jobs
- [ ] Group 7: IPC contract tests for ProcessJobRunner edge-cases
- [ ] Group 8: Formatting pass (ruff/black)

## Current group details
### Group 4 (done)
- [x] Debounce Jobs tab refresh on frequent job events
- [x] Throttle duplicate training progress emissions into Job events
- [x] Limit repeated identical training log lines sent into Job events
- [x] Add/adjust tests for new throttling behavior

### Group 5 (done)
- [x] Add TrainingRunSpec dataclass with JSON-serializable export
- [x] Add `deterministic` and `fast_local` training profiles
- [x] Apply profile settings in TrainModelUseCase before training starts
- [x] Add tests for profile behavior and serialization

### Group 6 (done)
- [x] Add shared run manifest helper (manifest + index + lookup by job_id)
- [x] Create manifests for training/detection/dataset jobs on start
- [x] Add "Open run folder" action in Jobs UI
- [x] Add tests for manifest registration and lookup
