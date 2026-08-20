# Milestones

Milestones are verified outcome checkpoints, not dates, schedules, or permission to implement. Epic/task approvals and dependency gates in the [workflow](../workflow/README.md) remain authoritative.

## Complete registry

1. [M1 — Vertical proof](M1-vertical-proof.md) — `planned`; 17 linked task definitions. A synthetic/redacted fixture enters through the historical adapter, known records resolve through a geocode cache, one API endpoint emits grouped GeoJSON, and the web app renders grouped pins with filters plus a source-date panel.
2. [M2 — Historical dataset ready](M2-historical-dataset-ready.md) — `planned`; 8 linked task definitions. The complete export is parsed with reconciled reports, locations are geocoded/reviewed, media is associated and stored, and public API queries meet correctness/performance targets.
3. [M3 — Public Dockerized MVP](M3-public-dockerized-mvp.md) — `done`; required E5/E6/E7 launch tasks complete with exit evidence recorded 2026-08-20. E7-T5 backups remain deferred (ADR-015). E8 live Telegram ingestion is M4 and awaits spike approval.
4. [M4 — Live Telegram updates](M4-live-telegram-updates.md) — `planned`; 5 linked task definitions. The historical checkpoint is reconciled with Telegram, and one hardened worker processes new/edit/delete events through the same ingestion core.

## Current delivery constraints

- M1 proves the accepted architecture with synthetic/redacted inputs before full-data work.
- M2 establishes reconciled historical data, reviewed coordinates/media, and correct/performant read contracts.
- M3 launches the Dockerized public MVP with HTTPS-gated restricted actions; an anonymous-only HTTP rehearsal may precede it.
- M4 starts only after M3 and live Telegram/geocoder gates are resolved.
- E1-T5 is cancelled under ADR-017; E7-T5 backups remain deferred under ADR-015 and are not an M3 launch gate.
- Proposed tasks are non-actionable. A milestone assignment never bypasses spike approval, promotion, implementation-plan approval, completed dependencies, or one-task-per-branch rules.

## Status interpretation

All milestones are currently `planned`. Each linked milestone file owns its exact outcome, current constraints, included task definitions, and exit evidence. A milestone becomes `done` only after every required task and every milestone-specific evidence item is complete; cancelled/deferred traceability entries do not silently become launch requirements.

See the [epic registry](../epics/README.md) for priorities, canonical M1 order, dependency normalization, task traceability, global definition of done, and product-requirement coverage.
