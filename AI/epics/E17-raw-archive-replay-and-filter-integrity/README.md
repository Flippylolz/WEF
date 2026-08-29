---
schema: ai-workflow/epic@1
id: E17
title: "Raw archive replay and filter integrity"
status: in_progress
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: null
---

# E17: Raw archive replay and filter integrity

## Outcome

Every incoming Telegram message (and each of its edits) is first landed verbatim in a
durable raw archive inside the application database and processed into canonical state
by a background stage, so a parser upgrade can be replayed over retained raw data
without a new export or Telegram traffic. Channel template variants stop degrading
data silently: prices written as `850 000злотых` parse as 850 000 PLN, and filter
facets come only from a backend-owned canonical vocabulary with reviewed typo
rerouting, eliminating mixed-case/misspelled duplicates such as `BiałOłęCka`,
`BiałOłęKa`, or `Praga PołUdnie`. The frontend renders backend-provided options and
applies no filter logic of its own.

## Priority and selection

- The owner selected E17 on 2026-08-29 after PR #197 fixed the immediate
  "Unknown location" defect and exposed the structural gaps this epic closes.
- Promoted tasks are expected to be `P1`: required for a safe public production
  launch state, not an active outage.
- E17 takes precedence over ordinary feature work until its production completion
  gate in E17-T6 is satisfied.

## Completion state (2026-08-30)

- E17-T1 done (PR #203), E17-T2 done (PR #208), E17-T3 done (PR #200),
  E17-T4 done (PR #201), E17-T5 done (PR #209) — each merged after every
  required CI check passed.
- E17-T6 is `ready` and blocked on the owner gate: a fresh Telegram data
  backup must be staged by the owner, replayed through the raw archive +
  replay pipeline into a production candidate, and promoted with recorded
  quality metrics. The epic becomes `done` only through that promotion.

## Completion gate (owner-controlled)

This epic is **not** `done` until the owner provides a fresh Telegram data backup and
that backup is replayed through the new pipeline and promoted to production
(E17-T6). Merging the implementation PRs is necessary but never sufficient; the
definition of done is the recorded production promotion evidence over the
owner-supplied backup.

## Verified problem evidence (2026-08-29)

- Live/existing rows tied to the shared `Unknown location` sentinel cannot be
  re-derived because checksum-unchanged messages are never re-extracted; no
  parser-version replay path exists (`RunMode.REPROCESS` is an unused enum value).
- `💸Цена:850 000злотых` currently extracts as **850** with unknown currency
  (reproduced against the `e2-v4` parser; the `_NUMBER` trailing word boundary
  rejects the grouped form before an untracked currency word).
- District filter facets are `SELECT DISTINCT location.district` over raw stored
  source text (`browse_adapter.py`), matched exactly and case-sensitively
  (`LocationRow.district.in_(...)`, `map_query_adapter.py`), so source typos and
  case variance surface as duplicate filter options.
- Live extraction runs inline in the reconciliation/backfill loop
  (`telegram_events.py`, `telegram_backfill.py`); the only complete raw dump is the
  operator-staged Telegram export outside the database.

## Governing documents

- [ADR-006: Shared ingestion core](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-012: Backend-centric modular monolith](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-021: Cached provider-neutral geocoding](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md)
- [Ingestion pipeline](../../ingestion/PIPELINE.md)
- [Ingestion geocoding](../../ingestion/GEOCODING.md)
- [Delivery workflow](../../workflow/README.md)
- [E15: Telegram ingestion reliability recovery](../E15-telegram-ingestion-reliability/README.md)
- [E8: Telegram live ingestion](../E8-telegram-live-ingestion/README.md)

## Workspace state

- [Spike](SPIKE.md): revision 1, owner-approved 2026-08-29.
- [Implementation plan](IMPLEMENTATION_PLAN.md): revision 1, owner-approved
  2026-08-29.
- [E17-T1](tasks/E17-T1-raw-event-archive-and-background-processing.md) through
  [E17-T6](tasks/E17-T6-owner-backup-replay-and-production-promotion.md): promoted
  2026-08-29; `tasks/` is the single authoritative location (no `proposed-tasks/`
  remains).
- Completion gate: epic becomes `done` only through E17-T6's owner-supplied backup
  replay and production promotion evidence.
