# Milestones

Milestones are verified outcome checkpoints, not dates, schedules, or permission to implement. Epic/task approvals and dependency gates in the [workflow](../workflow/README.md) remain authoritative.

## Complete registry

1. [M1 — Vertical proof](M1-vertical-proof.md) — `done`; the synthetic PostGIS/API/generated-client map path and its workflow evidence are complete.
2. [M2 — Historical dataset ready](M2-historical-dataset-ready.md) — `done`; complete-export reconciliation, geocoding/review, media, and API correctness/performance evidence are complete.
3. [M3 — Public Dockerized MVP](M3-public-dockerized-mvp.md) — `done`; required E5/E6/E7 launch tasks and live HTTPS evidence were recorded 2026-08-20. E7-T5 backups remain deferred under ADR-015.
4. [M4 — Live Telegram updates](M4-live-telegram-updates.md) — `planned`; code and the production service are delivered, but the 2026-08-27 missed-message incident makes E15's blocker-priority reconciliation/health/recovery evidence mandatory.
5. [M5 — Production maturity](M5-production-maturity.md) — `planned`; E17, E18, and E19 are `done`; E14-T1–T9 plus existing E7-T5 as a recovery prerequisite remain. The live service is maintainable, measurably reliable, observable, release-hardened, and restored from off-host backup in rehearsal.

## Current delivery constraints

- M1 proved the accepted architecture with synthetic/redacted inputs.
- M2 established reconciled historical data, reviewed coordinates/media, and correct/performant read contracts.
- M3 launched the Dockerized public MVP with HTTPS-gated restricted actions.
- M4 is blocked in operational acceptance: D-002 is resolved and the worker is deployed,
  but D-003/B-003 plus selected E15 retain the source-gap, truthful-health, and outage-recovery gates.
- M5 follows the post-launch E14 approval sequence; its disaster-recovery exit remains blocked until the owner supersedes or re-accepts ADR-015 and handles E7-T5 under valid approvals.
- E1-T5 is cancelled under ADR-017; E7-T5 backups remain deferred under ADR-015 and are not an M3 launch gate.
- Proposed tasks are non-actionable. A milestone assignment never bypasses spike approval, promotion, implementation-plan approval, completed dependencies, or one-task-per-branch rules.

## Status interpretation

M1, M2, and M3 are `done`; M4 and M5 remain `planned`. Each linked milestone file owns its exact outcome, current constraints, included task definitions, and exit evidence. A milestone becomes `done` only after every required task and every milestone-specific evidence item is complete; cancelled/deferred traceability entries do not silently become launch requirements.

See the [epic registry](../epics/README.md) for priorities, canonical M1 order, dependency normalization, task traceability, global definition of done, and product-requirement coverage.
