# Backend completion pass

Status: backend package complete under the owner's 2026-10-19 repository-wide
coverage request. All 233 executable backend files now have independent 100%
combined line/branch requirements. Local pytest, Compose, shared CI and the
per-report badge gate also require 100%.

## Verified package result

The locked Python 3.13.16/PostGIS run passes 2,260 tests with every one of its
18,267 statements and 3,886 branch paths covered. Coverage includes all 242 package
Python files, including unimported files; nine contain no executable counters.
The frontend retains its independent 100% requirements for every metric and file.
The final locked `make format-check lint typecheck test contract-check quality-gates`
run passes, including 2,260 backend tests, 311 frontend tests and 197 operational
policy/proof tests. Both application reports measure exactly 100%.

The added cases exercise real application behavior and failure boundaries:

- Operator composition checks explicit mutation controls, resource cleanup,
  acknowledged progress, bounded queries and redacted CLI receipts.
- HTTPX mock transports check wire bodies, client cleanup, quota/timeouts,
  malformed provider envelopes and stable request/result identities. A controlled
  monotonic clock verifies minimum request spacing independently of runner speed.
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
artifacts. This pass adds no coverage pragmas or runtime-file exclusions. Type-only imports
remain outside executable behavior.

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
- Freezing a dictionary always returns an immutable mapping. The parse-issue
  backfill retains that typed contract without an impossible non-mapping branch;
  its regression checks nested freezing and preservation of the original input.
- Hosted geocoding counts remaining retries explicitly. Tests assert exactly one
  initial call plus the configured retries and immediate quota refusal. The
  unreachable post-loop fallback is removed.

## Enforcement and remaining repository scope

The package keeps branch tracking and its complete source inventory. The quality
mapping rejects weakened thresholds, disabled branch tracking or a narrowed source
list. Every executable file is named in `.github/critical-coverage.json` at 100%;
missing reports, invalid counters and rounded percentages cannot pass.

Run `make format-check lint typecheck test contract-check quality-gates` with the
locked toolchain before pushing. The deliberate-fault tests cover a 99% backend
or badge floor and removal of the complete package/branch settings.

This package milestone does not complete repository-wide coverage. Operational
Python/shell, backend admin JavaScript, handwritten migrations and build entry
points still require measured coverage. The operational audit passes its existing
196 tests; a separate diagnostic reports 56.96% for Python operations after excluding
only test/proof drivers. It is not a completion result. Operational guards,
transfers and deployment behavior stay in scope. All applicable final global,
per-file and badge thresholds must require 100% before the overall goal is complete.
