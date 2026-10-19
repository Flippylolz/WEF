# Critical-path confidence (E14-T2)

The backend requires 100% combined line/branch coverage globally and independently
for all 262 executable package and migration files. Frontend lines, branches, functions
and statements now require 100% in every runtime file, with the source inventory
and exclusions described in [COVERAGE.md](COVERAGE.md).
`.github/critical-coverage.json` additionally enforces these independently measured
files. Missing/ambiguous reports, missing files, zero/invalid counters or weakened
floors fail closed. High aggregate coverage cannot hide a low critical module.

| Behavior and owner | Independent floor | Failure evidence |
| --- | --- | --- |
| Identity domain / unit | 100% combined | Username/password bounds, disabled/expired/revoked account/session and indistinguishable auth refusal tests; password-policy fault sample |
| All 20 backend domain implementations / unit + existing PostGIS suites | 100% combined independently for each | [Domain validation evidence and one exhaustive-enum branch exception](BACKEND_DOMAIN_COVERAGE.md); inconsistent parser/report/media values, missing reconciliation evidence and unsupported geocoder inputs fail closed |
| Catalog, contacts, estates and identity applications / unit + PostGIS/API | 100% combined independently for all 16 implementations | [Public application coverage](PUBLIC_APPLICATION_COVERAGE.md), including account lifecycle refusals, cursor/filter bounds, pagination/visibility, contact privacy, favorites and view history |
| Ingestion extraction, numeric/inventory parsing, replay planning, persistence and storage projections / unit + PostGIS | 100% combined independently for six implementations | [Extraction and projection evidence](INGESTION_PROJECTION_COVERAGE.md), including ambiguous quotes, bounded room counts, exact source spans, contact overlaps and protected/coupled replay values |
| Raw replay application / unit + PostGIS | 100% combined | Invalid/non-derivable archives, five-round bound, failed run/redaction, cancellation unlock and no false success; real version/sentinel replay |
| Import/dry-run orchestration, raw archive draining, media recovery and worker health/status/supervision / unit + PostGIS | 100% combined independently for seven implementations | [Orchestration coverage evidence](INGESTION_ORCHESTRATION_COVERAGE.md), including malformed-source progress, durable provider reservations, fenced recovery receipts, lease renewal, bounded claims and fail-closed worker diagnostics |
| Web auth transport / unit | 100% lines and branches | Refused/expired sessions, cancellation, empty/malformed responses and request failure mapping; no browser-owned authorization rule |
| Web map search state / unit | 100% lines and branches | URL/filter/selection round trips, numeric overflow and invalid timestamp normalization |
| Release gate / operational proof | Explicit branch assertions | Unassociated main pushes rejected, only configured valid events allowed; deliberate unconditional-acceptance fault |
| Historical import command / unit + existing PostGIS suites | 100% combined | [Operator stage evidence](IMPORT_COMMAND_COVERAGE.md): immutable source claims, acknowledged progress, no-work/replay skips, stable quota/transient pauses, bounded media batches and verification before success |
| All 23 transfer Python files and both coverage-policy checkers / operational tests | 100% combined independently per file | [Transfer evidence](TRANSFER_OPERATIONS_COVERAGE.md): corrupted bundles, capacity/collision refusals, SQL guards, interruption and checkpoint resume, subprocess entrypoints and deliberate policy drift |
| Historical activation and shared-edge preflight / operational tests | 100% combined independently per file | [Activation/preflight evidence](ACTIVATION_PREFLIGHT_COVERAGE.md): occupied host locks, identity mismatch, pointer restoration, semantic HTTPS failures, certificate permissions, listener/network and upstream refusals |
| Release state, order, observations, cache, outcome report and cohort evidence / operational tests | 100% combined independently per file | [Release-evidence cases](RELEASE_EVIDENCE_COVERAGE.md): inconsistent links/source ancestry, failed metadata/artifact reads, exact byte limits, symlinks, foreign attempts and insufficient health observations |
| Scheduled Dependabot controller / synthetic policy/process tests | 100% combined | [Verified merge-evidence cases](DEPENDABOT_EVIDENCE_COVERAGE.md): required check success, unavailable conclusions, nonempty commit evidence, GitHub identities, owner-label history, second snapshots and simulated merge refusal |
| Shared-edge release, inventory and staged cutover / synthetic filesystem/process tests | 100% combined independently per file | [Rollback and listener cases](SHARED_EDGE_ROLLBACK_COVERAGE.md): distinct rollback target, reload restoration, legacy self-rollback refusal, correct TCP/UDP addresses, Forecast/unrelated drift and failed cutover restoration |
| Production and candidate configuration builders/validators / synthetic env/file/CLI tests | 100% combined independently per file | [Configuration boundaries](RELEASE_CONFIGURATION_COVERAGE.md): private non-overwriting files, required credentials, parser/identity/path/image validation, provider settings and loopback/database containment |
| Release checksums, manifest and verified artifact reuse / synthetic file/API/CLI tests | 100% combined independently per file | [Artifact integrity and fallback](RELEASE_ARTIFACT_COVERAGE.md): malformed JSON shapes, source/digest/definition identity, corrupt/duplicate/foreign/missing files, unusable downloads and safe full-verification fallback |

Combined coverage counts executed lines and branch paths, without rounding before
comparison. Frontend floors check lines and branches separately. Baseline measurement
on T1's code plus T2 tests: replay and reveal 100%; persistence 98.35%; map 96.47%;
browse 96.19%; provider budget 96.43%; identity application 93.21%. These are diagnostic
measurements, not probabilities of correctness.

## Deliberate faults and determinism

`prove_critical_faults.py` copies only checked-in backend source/tests/config and
scripts into a temporary directory. It strips database/provider environment values,
uses no external account, and never mutates the checkout. Three baseline runs use
PYTHONHASHSEED 0, 17 and 91 (reversing file order for seed 17), then five unique replacements weaken password length,
bypass hidden-contact refusal, remove bbox ordering, invert replay checksum selection,
and accept unassociated releases. Every baseline must pass; every fault must fail
its focused test with an assertion/test-failure exit, not an import/collection failure.
Target drift is an error. No silent retries are added. This is a bounded sample,
not an exhaustive mutation score or proof that all test ordering is irrelevant.

## Remaining behavior outside completed per-file floors

Application SQL adapters, CLI composition and frontend optional-field combinations
now have complete independent floors. Their database, transport, setup, failure
and privacy assertions remain required alongside coverage. Operational deployment
Python and shell still require additional cases before the owner's repository-wide
100% goal is complete. Transfer files retain their completed floors while those
remaining gaps are closed. Completed coverage floors cannot be weakened to
accommodate a refactor.

Full-stack/WebGL/mobile/accessibility ownership belongs to E14-T5. Current unit and
map-disabled browser tests do not satisfy it. No production load, data, provider
request, source fixture, public contract or parser behavior changes in T2.
