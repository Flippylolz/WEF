---
schema: ai-workflow/implementation-plan@1
epic: E17
title: "Raw archive replay and filter integrity delivery"
status: approved
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E17-T1
    revision: 1
  - id: E17-T2
    revision: 1
  - id: E17-T3
    revision: 1
  - id: E17-T4
    revision: 1
  - id: E17-T5
    revision: 1
  - id: E17-T6
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "owner"
  decided_at: "2026-08-29T17:10:10Z"
  approved_revision: 1
  evidence: "ZCode session owner instruction on 2026-08-29: implement this epic; PR merges are allowed after the CI is green"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Raw archive replay and filter integrity delivery

## Approved spike baseline

- [E17 spike revision 1](SPIKE.md) was owner-approved on 2026-08-29.
- The binding recommendations are: an append-only raw-event archive drained by a
  background stage; parser-version replay re-import over the archive; reviewed
  currency-word vocabulary for prices; write-time canonical district vocabulary with
  a reviewed reroute table; backend-owned filter facets with a render-only frontend;
  and an owner-gated backup replay/promotion completion gate.

## Scope and outcome

Deliver six independently reviewable changes so that (1) no Telegram event can be
lost or silently mis-processed, (2) parser upgrades can be replayed without new
Telegram traffic or operator-staged exports, (3) prices written as
`850 000злотых` store the correct magnitude and currency, (4) filter facets contain
only canonical district values with reviewed typo rerouting, (5) filter behavior is
deterministic under tests, and (6) the epic's completion is recorded only after the
owner supplies a fresh backup that is replayed and promoted to production.

## Ordered task sequence

Implementation order optimizes for independent review and early value; dependency
order is preserved.

1. [E17-T3](tasks/E17-T3-currency-word-and-grouped-number-parser-hardening.md) —
   small, dependency-free parser repair shipped first; bumps the parser version.
2. [E17-T4](tasks/E17-T4-canonical-filter-vocabulary-and-typo-rerouting.md) —
   dependency-free write-time canonicalization, reroute table, facet/matching
   canonicalization, and minimal render-only frontend adjustments.
3. [E17-T5](tasks/E17-T5-filter-determinism-and-test-coverage.md) — depends on T4's
   canonical vocabulary; determinism fixes and the flake audit.
4. [E17-T1](tasks/E17-T1-raw-event-archive-and-background-processing.md) — the
   foundation slice: raw-event table, landing, drainer, worker integration.
5. [E17-T2](tasks/E17-T2-parser-replay-reimport.md) — depends on T1; the replay
   operator command and repair of stale-parser rows.
6. [E17-T6](tasks/E17-T6-owner-backup-replay-and-production-promotion.md) — the
   owner-gated completion gate; blocked on the owner's backup, not schedulable by
   implementation alone.

## Cross-task architecture

- The canonical district vocabulary stays in the ingestion domain beside
  `canonical_warsaw_district`; catalog adapters consume it, preserving the inward
  dependency contracts verified by `lint-imports`.
- The raw archive stores verbatim payloads only; canonical interpretation happens
  exclusively in the drainer through the unchanged `extract_listing` +
  `persist_live_upsert` path, so replay and live processing share one code path.
- Replays reuse revised-offer semantics (revision anchoring, visibility, dedup
  fingerprints) rather than inventing a second write path.
- The geocode budget/sentinel guards from PR #197 are never bypassed by replay.

## Tests and validation

- Every task lands unit tests plus disposable-PostGIS integration coverage where a
  migration or SQL behavior is touched; `make lint`, `make typecheck`,
  `make format-check`, `make contract-check`, and `make test` gate every PR.
- T5 adds a dedicated determinism/flake suite; CI must pass with zero
  order-dependent variance.

## Migrations and rollout

- One new Alembic migration (T1) adds `telegram_raw_events`; it is additive with no
  backfill and no downtime requirement. Rollback drops the table.
- No other schema changes; T4 repairs existing rows through the T2 replay/T6 backup
  import, never through a data migration.

## Risks

- Worker liveness (E15 bounds) — the drainer runs in bounded batches; landing an
  event is a single insert and is strictly cheaper than today's inline processing.
- Raw table growth — retained indefinitely by default under E14 capacity monitoring;
  retention policy is an owner decision recorded at T6 if it changes.

## Completion

- E17 is not `done` until E17-T6 records the owner-supplied backup replay and
  production promotion evidence in the epic README.
