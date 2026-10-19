# Backend completion pass

Status: in progress under the owner's 2026-10-19 repository-wide coverage request.
The remaining backend package gaps are being closed together so the final change
can enable its 100% gate. The existing global 90% floor remains until the full
locked run actually reaches 100%; completed independent module floors remain at
100% throughout.

## Verified checkpoint

The locked Python 3.13.16/PostGIS run passes 2,022 tests at 97.52% combined
line/branch coverage. Another 354 lines and 196 branch paths remain uncovered.
All 83 completed implementation floors require 100% independently. The complete
format, lint, type, test, contract and quality-gate validation passed at the earlier
1,968-test checkpoint, including 311 frontend tests and 196 operational policy/proof
tests. Later archive/admin cases pass the full backend suite; the final change must
rerun every required check. Further projection/backfill cases pass focused checks
after this checkpoint.

The added cases exercise real application behavior and failure boundaries:

- Operator composition checks explicit mutation controls, resource cleanup,
  acknowledged progress, bounded queries and redacted CLI receipts.
- HTTPX mock transports check wire bodies, client cleanup, quota/timeouts,
  malformed provider envelopes and stable request/result identities.
- PostGIS transactions check stale/concurrent enrichment writes, protected field
  origins, owner-scoped history, normalized developments, encrypted contact
  backfill, lease fencing and recurring run identity.
- Real parser replay preserves original source evidence, requeues a legacy
  equivalent observation's media recovery and lets new address evidence replace
  only the unresolved location sentinel.
- Application tests check missing-only fills, calibrated evidence, budget deferrals,
  malformed proposals, owner isolation and conservative automatic recovery.
- The owner console checks lifecycle controls, denied or stale links, form filters,
  optional map evidence and typed redacted exports.
- Telegram and filesystem tests check source ordering, media replay skips, lease
  ownership, byte limits, cancellation, metadata, image modes, atomic publishing
  and source changes during a read.

All source, contacts, keys and provider responses in these cases are synthetic.
No provider account or production source is used. Reports remain ignored local
artifacts. This pass adds no coverage exclusions.

## Equivalent control-flow simplifications

The production changes remove redundant paths while retaining reachable validation:

- Currency aliases already contain every supported ISO currency code; tests check
  all four codes. The duplicate fallback is removed.
- Evidence search continues until a safe match or the existing not-found refusal.
  The unreachable loop exit is removed; contact-only matches still fail closed.
- Media grouping emits one disposition per input descriptor; the existing empty
  work check handles the result without a duplicate earlier return.
- Live event construction rejects inconsistent new/edit/delete shapes. Consumers
  use that validated message type; the final enum case handles deletion. Constructor
  failure tests retain the boundary instead of bypassing immutable event creation.
- The public media query admits only WebP and JPEG variants. The mapper handles
  those two cases after skipping null outer-join results.
- Hosted geocoding counts remaining retries explicitly. Tests assert exactly one
  initial call plus the configured retries and immediate quota refusal. The
  unreachable post-loop fallback is removed.

## Completion requirements

The backend must include all package files in coverage, preserve branch tracking
and existing critical floors, and test reachable failure paths. Documentation,
generated declarations, test infrastructure and type-only/protocol declarations
are outside executable behavior. Any structural exception requires a local reason
and evidence of its invariant; runtime modules cannot be removed from the report
to reach the target.

After the remaining package gaps are closed, raise its applicable global and
per-file gates to 100%, update policy-drift proofs and run
`make format-check lint typecheck test contract-check quality-gates` with the locked
toolchain. Preserve the frontend's existing per-file 100% requirements.

This package milestone alone does not complete repository-wide coverage.
Operational Python/shell, backend admin JavaScript, handwritten migrations and
runtime behavior outside the application source reports still require an explicit
inventory and appropriate coverage. Every applicable final global, per-file and
badge threshold must require 100% before the overall goal is complete.
