# Ingestion orchestration coverage

The owner's repository-wide coverage request includes import orchestration,
background recovery and worker health. This pass adds 43 cases and independent
100% combined line/branch floors for seven implementations, with 620 statements
and 134 branch paths:

- `complete_import.py` and `dry_run.py`.
- `raw_archive.py` and `media_recovery.py`.
- `telegram_worker_liveness.py`, `telegram_worker_status.py` and
  `telegram_worker_supervision.py`.

The [critical coverage policy](../../.github/critical-coverage.json) preserves
completed work independently of the remaining backend aggregate gaps.

## Behavior evidence

| Boundary | Assertions |
| --- | --- |
| Import preparation | Progress accounts for every scanned record, including malformed records that cannot enter canonical persistence |
| Durable provider reservations | A future reservation is awaited after budget reservation and before the provider request or terminal charge |
| Dry-run projections | Publication bounds preserve timestamp ties; exact-threshold and one-below decisions have distinct audit buckets; absent content types are not invented; unassociated media reconcile into reason counts |
| Archive ownership | Batch sizes are bounded; processing holds its serialization lock; mismatched receipt UUIDs fail; repeated terminal receipts do not count as new progress |
| Archive failure ledger | A ledger outage preserves the original processing error and its cause; recovery finishes only claimed batches with their actual failure state |
| Media ownership | A cycle claims at most ten items and renews ownership before delayed work can complete |
| Worker health documents | Nonobjects, invalid timestamps, nonstring diagnostics and negative/boolean/noninteger source IDs fail closed; missing or malformed runtime health cannot pass liveness |
| Heartbeat failures | Write failures retain only their safe category, propagate the original exception and remove stale health files |
| Supervision and status | An empty critical stage set is refused; the pending reconciliation slot waits for shutdown; configured credentials without a session produce an actionable status note |

The tests are [orchestration boundaries](../../apps/backend/tests/test_ingestion_orchestration_boundaries.py)
and [worker runtime boundaries](../../apps/backend/tests/test_worker_runtime_boundaries.py).
They use synthetic source records, a fake clock, in-memory ports and temporary
files. Provider delays and failures are simulated; no provider account or
production data is used.

## Structural branch exception

`MediaDisposition` rejects both an absent association/reason pair and inconsistent
ownership. Therefore a disposition without an association always has a reason.
The dry-run accumulator retains its defensive `if reason is not None` guard with
a documented `pragma: no branch` for its impossible false path. Existing
[domain invariant tests](../../apps/backend/tests/test_media_grouping.py) enforce
that contract, and the new valid unassociated-media test executes its counter.
No reachable error handler or runtime file is excluded.

Run `make coverage-backend` for locked Python/PostGIS coverage. The combined run
passes 1,646 tests at 92.55% backend coverage, with all 49 completed implementation
floors passing. Another 1,117 lines and 535 branch paths remain uncovered.
Remaining transport orchestration, admin services, adapters, commands and
operational code stay in scope. All applicable global, per-file and badge thresholds must require 100%
before the repository-wide goal is complete.
