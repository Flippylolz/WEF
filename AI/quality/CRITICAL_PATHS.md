# Critical-path confidence (E14-T2)

The global backend branch-aware and frontend line/branch floors remain 90%.
`.github/critical-coverage.json` additionally enforces these independently measured
files. Missing/ambiguous reports, missing files, zero/invalid counters or weakened
floors fail closed. High aggregate coverage cannot hide a low critical module.

| Behavior and owner | Independent floor | Failure evidence |
| --- | --- | --- |
| Identity domain / unit | 98% combined | Username/password bounds, disabled/expired/revoked account/session and indistinguishable auth refusal tests; password-policy fault sample |
| Identity application / unit + PostGIS | 92% combined | Authentication/session/password reset/bootstrap refusal; API authorization and persistence tests |
| Contact reveal / unit + PostGIS/API | 98% combined | Hidden offers with stored contacts never decrypt; password-change/rate/key failures; malformed ciphertext; minimized audits; normalized dedupe and clearing |
| Map query / unit + PostGIS | 95% combined | Finite/ordered/bounded bbox, filter conflicts, stable ETags and backend visibility; inverted-bbox fault sample |
| Browse application / unit + PostGIS | 95% combined | Pagination/order/filter validation and public projection boundaries |
| Persistence application / unit + PostGIS | 97% combined | Atomic batches, immutable source identity, revisions, duplicate/reordered replay, transaction failure and cancellation |
| Raw replay application / unit + PostGIS | 98% combined | Invalid/non-derivable archives, five-round bound, failed run/redaction, cancellation unlock and no false success; real version/sentinel replay |
| Complete import / unit + PostGIS | 95% combined | Unchanged checksums skipped; daily/cycle budget boundaries, no-result/quota/transient outcomes and redacted charged exceptions |
| Web auth transport / unit | 98% lines, 91% branches | Refused/expired sessions and request failure mapping; no browser-owned authorization rule |
| Web map search state / unit | 98% lines, 94% branches | URL/filter/selection round trips and invalid input normalization |
| Release gate / operational proof | Explicit branch assertions | Unassociated main pushes rejected, only configured valid events allowed; deliberate unconditional-acceptance fault |

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

## Explicit behavior coverage outside per-file floors

SQL adapters and CLI composition contain database/transport/setup branches whose
uniform execution percentage would encourage tests that merely repeat wiring.
Existing real PostGIS suites own persistence transactions, migrations, conflicts,
source-version protection, favorites/visibility and contact audit/privacy. Operator
CLI tests own malformed options, missing prerequisites, redacted output, dry-run and
exit behavior. These are retained under the global floor; they are not excluded from
coverage. The API client DTO optional-field combinations likewise remain globally
measured and covered by request/error/contract tests instead of requiring every
optional-field combination. T3/T4 refactors must retain these behaviors.

Full-stack/WebGL/mobile/accessibility ownership belongs to E14-T5. Current unit and
map-disabled browser tests do not satisfy it. No production load, data, provider
request, source fixture, public contract or parser behavior changes in T2.
