# Shared-edge rollback and inventory evidence

The owner's repository-wide coverage request exposed two deployment defects:
activating TLS and then redirects within one release replaced the distinct rollback
target with the current release, and the combined TCP/UDP listener collector read
the queue column instead of the local address. Synthetic regressions reproduce
both defects without contacting a host or changing a running edge.

## Corrected behavior

A configuration change within the current release retains the last distinct release
as its rollback target. If its reload callback fails, the prior active configuration
and current pointer are restored and the successful state record remains unchanged.
Activating a different release still records the former current release for rollback.
A legacy record whose previous release equals its current release is refused before
validation or pointer changes; it cannot report a successful restoration.

Listener capture reads the local-address column of `ss -H -lntu`, retains protocol
and address, sorts/deduplicates watched listeners and refuses malformed nonempty
rows. Missing `ss` and command failures remain errors. The specific Forecast drift
check runs before the general unrelated-container guard, making its diagnostic
reachable while preserving both refusals.

## Operational compatibility

Existing self-referential rollback records require an operator to identify an
earlier validated release and activate it explicitly through the existing release
CLI. The fix does not infer or rewrite historical state. See the
[Nginx recovery procedure](../operations/NGINX_TLS.md#migration-and-rollback).

Inventory schema `wef-shared-edge-inventory@1` remains unchanged, but listener
strings now contain protocol plus address. Recapture both before and after
snapshots with the same corrected collector revision; do not compare an old
collector's missing listener evidence with a corrected capture. No live host,
listener, certificate, Forecast resource or application state was changed by this
coverage work.

## Regression and coverage evidence

Twenty-one new cases and the existing twelve cases cover all 431 statements and
116 branch paths in `shared_edge_release.py`, `shared_edge_inventory.py` and
`shared_edge_cutover.py`. Each file has an independent 100% operational floor,
with deliberate policy faults rejecting a removed floor. Only the existing four
type-checking-only lines are excluded; runtime exclusions and dependencies are
unchanged.

Tests use temporary rendered release trees and synthetic process results. They
assert distinct rollback targets, failed reload restoration, legacy-state refusal,
path/symlink boundaries, Nginx UID/read-only mount/network arguments, upstream and
reload failures, redacted inventory collection, watched listeners, unrelated and
Forecast drift, staged cutover failure/rollback behavior and real safe CLI paths.
The real entrypoints only reject invalid fixture inputs or print a dry plan.

This corrects the existing reversible-cutover and non-interference acceptance
criteria in [E7-T9](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md)
under the owner's unplanned quality request. Remaining operational Python, shell
and substantive embedded Python remain required before completing the overall goal.

## Comparable operational audit

The native diagnostic with the same existing release, topology and rollback proof
drivers rises from 83.86% to 89.02%. All 4,678 statements and 1,450 branch paths
remain in its inventory; 485 lines and 188 branch paths are still uncovered.
Reports stay ignored. The required locked operational test report and its per-file
floors remain the CI gate; the native audit is a broader progress diagnostic.

## Validation

The full locked `make format-check lint typecheck test contract-check quality-gates
compose-config` passes: 2,266 backend and 355 frontend tests retain 100%, and all
309 operational tests pass with 37 independent 100% file floors. The locked release
workflow proof, all 33 focused cases, strict Ruff/mypy, Markdown links and Git
whitespace checks also pass. Synthetic rollback/topology proofs complete in the
comparable native audit; no production recovery or live Nginx reload was attempted.
