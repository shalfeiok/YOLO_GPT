# Full repository review (2026-02-20)

This document captures the latest repository-wide assessment and concrete remediation plan.
It is synchronized with the detailed assistant report provided in chat.

## Quick highlights
- Core layering and use-case boundaries are present (`app/application/use_cases`, `app/application/ports`).
- Tooling baseline exists (`ruff`, `black`, `mypy`, `pytest`, coverage threshold).
- Current CI quality gate is red due to lint/type/test issues in headless Linux environments.

## Immediate actions
1. Fix headless import path for `app.ui.infrastructure` to avoid importing Qt GUI modules at package import time.
2. Make lint green for `app/application/container.py` (duplicate import, unused imports) and start module-by-module `ruff --fix` rollout.
3. Resolve highest-impact mypy errors in `app/core/jobs/*` and `app/ui/infrastructure/*`.
4. Split `app/ui/views/detection/view.py` into presenter/controller/services to reduce coupling and enable unit tests.
5. Add security hardening for generated-script execution in `app/features/ultralytics_solutions/service.py`.
