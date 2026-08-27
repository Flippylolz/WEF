# Milestones

Milestones are verified outcome checkpoints, not dates, schedules, or permission to implement. Epic/task approvals and dependency gates in the [workflow](../workflow/README.md) remain authoritative.

## Complete registry

1. [M1 — Vertical proof](M1-vertical-proof.md) — `done`; the synthetic PostGIS/API/generated-client map path and its workflow evidence are complete.
2. [M2 — Historical dataset ready](M2-historical-dataset-ready.md) — `done`; complete-export reconciliation, geocoding/review, media, and API correctness/performance evidence are complete.
3. [M3 — Public Dockerized MVP](M3-public-dockerized-mvp.md) — `done`; required E5/E6/E7 launch tasks and live HTTPS evidence were recorded 2026-08-20. E7-T5 backups remain deferred under ADR-015.
4. [M4 — Live Telegram updates](M4-live-telegram-updates.md) — `planned`; code and the production service are delivered, but verified live entity/event delivery, gap reconciliation, and outage-recovery evidence remain open.
5. [M5 — Production maturity](M5-production-maturity.md) — `planned`; E14-T1–T9 plus existing E7-T5 as a recovery prerequisite. The live service is maintainable, measurably reliable, observable, release-hardened, and restored from off-host backup in rehearsal.

## Current delivery constraints

- M1 proved the accepted architecture with synthetic/redacted inputs.
- M2 established reconciled historical data, reviewed coordinates/media, and correct/performant read contracts.
- M3 launched the Dockerized public MVP with HTTPS-gated restricted actions.
- M4 is in operational acceptance: D-002 is resolved, the worker is implemented/deployed, and D-003/B-003 retains the remaining live-evidence gate.
- M5 follows the post-launch E14 approval sequence; its disaster-recovery exit remains blocked until the owner supersedes or re-accepts ADR-015 and handles E7-T5 under valid approvals.
- E1-T5 is cancelled under ADR-017; E7-T5 backups remain deferred under ADR-015 and are not an M3 launch gate.
- Proposed tasks are non-actionable. A milestone assignment never bypasses spike approval, promotion, implementation-plan approval, completed dependencies, or one-task-per-branch rules.

## Status interpretation

M1, M2, and M3 are `done`; M4 and M5 remain `planned`. Each linked milestone file owns its exact outcome, current constraints, included task definitions, and exit evidence. A milestone becomes `done` only after every required task and every milestone-specific evidence item is complete; cancelled/deferred traceability entries do not silently become launch requirements.

See the [epic registry](../epics/README.md) for priorities, canonical M1 order, dependency normalization, task traceability, global definition of done, and product-requirement coverage.
