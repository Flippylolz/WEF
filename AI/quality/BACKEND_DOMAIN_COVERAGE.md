# Backend domain coverage

The 2026-10-19 coverage work adds 57 tests for domain failure cases and raises
every current backend domain implementation to 100% line/branch coverage. The
20 behavior-bearing domain modules contain 1,739 executable statements and 420
branch paths. Five namespace/re-export modules are also measured at 100% through
the behavior tests that import their contracts.

[The critical coverage policy](../../.github/critical-coverage.json) enforces a
100% combined line/branch floor independently for each of those 20 implementations.
Missing files, invalid counters and shortfalls fail closed. This preserves the
completed domain work while application services, adapters and operators continue
toward the repository-wide target.

## Behavior evidence

| Boundary | Assertions |
| --- | --- |
| Dry-run values and reports | Missing identities/versions/checksums, negative counts/timings, unordered dates, inconsistent completion/error states and unreconciled source/candidate/media/warning totals raise their documented errors |
| Parser evidence | Candidate thresholds/classification and listing identity remain coherent; contacts and HTTP links must reference evidence from their own rule; warnings require field identifiers |
| Media ownership | Associations require listing identity and rule versions; unread observations cannot own stored originals; verified media must own an original; checksum mismatches require observed bytes |
| Worker health | A running reconciliation stage without a completed reconciliation remains unhealthy |
| Geocoding | Empty candidate sets and ambiguous address evidence are refused; unsupported or unresolved display fragments preserve honest fallback text |
| Canonical source JSON | Finite fractional values survive normalization; serializer failures retain a stable domain error and their original cause |
| Contacts | A lone plus sign is preserved without inventing phone digits |
| Estate localization | Every enum member has its exact backend-owned translation key; adding an unhandled member fails the mapping assertion |

The new tests are [dry-run domain validation](../../apps/backend/tests/test_dry_run_domain.py)
and [domain boundaries](../../apps/backend/tests/test_domain_boundaries.py).
[Location display tests](../../apps/backend/tests/test_location_display_name.py)
and [estate domain tests](../../apps/backend/tests/test_domain.py) extend existing
behavior assertions. All source text, identities and media metadata are invented
fixtures; no provider account or production data is used.

## One structural branch exception

`Availability.label_key` uses an exhaustive match over two enum members. Python
coverage otherwise requests a fall-through path after its last case, which cannot
be exercised by a valid `Availability`. A `pragma: no branch` on that final case
documents this structural exception. The complete enum-to-key mapping test fails
if a new member is introduced without updating the behavior and its expectation.
No source file, error handler or reachable domain path is omitted.

## Measurement and remaining work

The full locked Python 3.13.16/PostGIS measurement passed 1,549 tests. Backend
coverage increased from 91.36% to 91.86%; 1,208 lines and 598 branch paths outside
the domain layer remain uncovered. The global backend floor remains 90% until
those gaps are actually closed. Current domain coverage does not establish the
repository-wide goal: application services, persistence/provider adapters,
commands/workers and code outside the application reports still need coverage.

Run `make coverage-backend` for the real database-backed report and all independent
floors. The JSON report remains ignored at `tmp/coverage/backend/coverage.json`.
Format, lint, strict types, contract checks, policy tests and required PR CI remain
independent gates; coverage percentages do not replace behavioral assertions.
