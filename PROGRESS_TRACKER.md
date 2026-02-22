# Progress Tracker

## Plan (grouped commits)
- [x] Group 1: StackController error boundary (safe tab failures)
- [x] Group 2: Lazy first-open tab creation without UI freeze
- [x] Group 3: Jobs visibility for dataset/training/detection actions
- [ ] Group 4: Throttling/batching to reduce UI spam
- [ ] Group 5: TrainingRunSpec + reproducible profiles
- [ ] Group 6: Run manifests + open run folder from Jobs
- [ ] Group 7: IPC contract tests for ProcessJobRunner edge-cases
- [ ] Group 8: Formatting pass (ruff/black)

## Current group details
### Group 4 (in progress)
- [x] Debounce Jobs tab refresh on frequent job events
- [x] Throttle duplicate training progress emissions into Job events
- [x] Limit repeated identical training log lines sent into Job events
- [ ] Add/adjust tests for new throttling behavior
