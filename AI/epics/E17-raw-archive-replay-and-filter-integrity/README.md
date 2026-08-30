---
schema: ai-workflow/epic@1
id: E17
title: "Raw archive replay and filter integrity"
status: done
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
  E17-T4 done (PR #201), E17-T5 done (PR #209), E17-T6 done (PR #211) —
  each merged after every required CI check passed.
- Completion evidence: the owner's fresh backup (27,879 messages through
  2026-08-28) replayed with 100% location coverage, a clean 17-value
  canonical district vocabulary, verified price magnitudes, and a
  converging, idempotent archive replay; production promoted through
  Release and deploy production run 33280067325.
- Production repair completed 2026-08-30 over the host runbook: history
  seeded into the raw archive (27,866 rows), replay converged to zero
  stale/reprocessable items, 1,218 locations geocoded under budget,
  592 pins accepted, 3,055 offers visible, sentinel pin removed, and
  17 canonical facet districts live on the map (release 7a3e927).

## Completion gate (owner-controlled) — satisfied
>>>>>>> 7158019 (docs(E17-T6): record backup replay evidence and close the epic)

The owner staged the fresh Telegram data backup on 2026-08-30; it was replayed
through the new pipeline with recorded quality metrics and production was
promoted (Release and deploy production run 33280067325). See
[E17-T6](tasks/E17-T6-owner-backup-replay-and-production-promotion.md).

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
