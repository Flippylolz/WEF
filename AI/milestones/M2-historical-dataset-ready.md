---
id: M2
title: "Historical dataset ready"
status: done
---

# M2: Historical dataset ready

## Outcome

The complete export is parsed with reconciled reports, locations are geocoded/reviewed, media is associated and stored, and public API queries meet correctness/performance targets.

## Current constraints

- Source lineage, uncertainty, failure accounting, and source checksums remain reproducible.
- Only reviewed coordinates become visible pins; out-of-area and unresolved records remain reportable.
- Real source data and media remain outside Git, CI artifacts, and container image layers.
- This milestone does not itself authorize a production deployment.

## Included epic/task definitions

### [E2: Historical export parser and audit](../epics/E2-historical-export-parser-audit/README.md)

- [E2-T3: Implement deterministic media grouping](../epics/E2-historical-export-parser-audit/tasks/E2-T3-implement-media-grouping.md) — `done` through [PR #37](https://github.com/Flippylolz/WEF/pull/37)
- [E2-T4: Implement dry-run reports and operator wiring](../epics/E2-historical-export-parser-audit/tasks/E2-T4-implement-dry-run-reports.md) — `done` through [PR #40](https://github.com/Flippylolz/WEF/pull/40)
- [E2-T5: Audit the complete export](../epics/E2-historical-export-parser-audit/tasks/E2-T5-audit-the-complete-export.md) — `done` through [PR #42](https://github.com/Flippylolz/WEF/pull/42), with reconciled complete-export audit evidence

### [E3: Database, geocoding, and media pipeline](../epics/E3-database-geocoding-media/README.md)

- [E3-T4: Implement media storage and derivatives](../epics/E3-database-geocoding-media/tasks/E3-T4-implement-media-storage-and-derivatives.md) — `done` through PR #60
- [E3-T5: Import and review the complete dataset](../epics/E3-database-geocoding-media/tasks/E3-T5-import-and-review-the-complete-dataset.md) — `done` revision 3 through PRs #65/#66 with terminal local reconciliation (completion recorded 2026-08-17)

### [E4: Read API and filter contracts](../epics/E4-read-api-filter-contracts/README.md)

- [E4-T2: Implement facets and location offer collection](../epics/E4-read-api-filter-contracts/tasks/E4-T2-implement-facets-and-location-offer-collection.md) — `done` (M1; reused by M2)
- [E4-T3: Implement offer detail](../epics/E4-read-api-filter-contracts/tasks/E4-T3-implement-offer-detail.md) — `done`
- [E4-T4: Harden API behavior and performance](../epics/E4-read-api-filter-contracts/tasks/E4-T4-harden-api-behavior-and-performance.md) — `done`

Cancelled and deferred candidates remain linked for traceability but are not completion requirements unless an approved revision restores them to required scope.

## Exit evidence

- [x] The full export audit and final import counts reconcile with stable reason codes and source/parser identity.
- [x] Visible pins have accepted coordinates; unresolved/out-of-area/duplicate-suspect/missing-media records remain reportable.
- [x] Media associations, opaque storage, derivatives, and source relationships pass integrity checks.
- [x] Map/facet/collection/detail queries share contract semantics and meet documented correctness/performance evidence.
- [x] Every required task has been promoted, approved, dependency-gated, implemented on its dedicated branch, and completed with definition-of-done evidence.

Recorded 2026-08-20 after E3-T5 terminal reconciliation, E4-T3/T4 completion, and public activation of the historical candidate under M3/E7-T11.

## Status rule

`planned` records the current outcome checkpoint only; it grants no implementation permission. Change this milestone to `done` only when all required exit evidence and task completion records exist under the [workflow](../workflow/README.md).
