# Coverage scope and progress

The owner requested 100% code coverage on 2026-10-19, excluding documentation and
other files without application behavior. This is unplanned quality maintenance
under that direct request. Application behavior, API contracts, schema, providers
and production deployment configuration remain within their existing boundaries.

## Current enforced scope

The enforced coverage goal is 100% for every included runtime inventory,
independently per file. Documentation and the non-runtime exclusions below remain
outside the denominator.

| Inventory | Measured behavior | Required coverage |
| --- | --- | --- |
| Backend package and handwritten migrations | 18,839 statements and 3,930 branch paths; 262 executable files | 100% globally and per file |
| Frontend, build entrypoints and backend-owned owner map asset | 1,508 lines, 1,662 statements, 427 functions and 1,418 branches; 48 source files | 100% for all four metrics per file |
| Operational Python, including extracted deployment contracts | 4,901 statements and 1,520 branch paths; 56 executable files | 100% globally and per file |
| Runtime shell, including the Certbot deploy hook | 390 executable lines; 11 files | 100% lines per file |

[Runtime shell evidence](RUNTIME_SHELL_COVERAGE.md) closes the remaining measured
inventory and records the source policy, failure cases and isolated collector.
`make quality-gates` enforces both operational suites. The milestones below retain
the measurements from each completed pass.

## Frontend gate

Vitest measures every `src/**/*.{ts,tsx}` file, including files never imported by
tests. The inventory also includes `next.config.ts`, frontend `scripts/*.mjs` and
the backend-owned `place_picker.js` through explicit external-file measurement.
Lines, branches, functions and statements each require 100%, independently for
every file. Next.js entry points, middleware, error documents, translation
configuration, API clients, hooks and components are all measured.

The explicit file exclusions are:

| Exclusion | Reason |
| --- | --- |
| `coverageConfigDefaults.exclude` | Vitest's standard test, declaration, dependency, build and tooling exclusions |
| `src/generated/**` | OpenAPI-generated TypeScript declarations; contract generation/drift checks own these |
| `src/test/**` | Test environment setup and warning-gate self-tests |
| `src/**/*.test-support.tsx` | Fixtures, transport doubles and render helpers used by tests |

Documentation, styles, images and JSON data do not match the executable TypeScript
source inventory. They remain subject to their relevant link, formatting, build,
contract and browser checks; unit coverage does not measure them.

Four inline V8 exceptions retain defenses without manufacturing tests that violate
React's lifecycle:

- `account-modal.tsx` and `favorites-panel.tsx`: the null-ref return in effects for
  unconditional dialog elements. React assigns their refs before running effects.
- `map-explorer.tsx`: the same null-ref return for its unconditional filter dialog.
- `map-explorer.tsx`: the initial authentication-opener no-op. It has no behavior;
  the toolbar effect registers the real opener, whose interactions are tested.

Each exception has its reason next to the ignored expression/branch. No runtime
module, error handler, network adapter, query guard or browser fallback is omitted.
In particular, missing selections, denied storage, unavailable WebGL/dialog support,
map load deadlines and asynchronous cancellation/pagination are tested.

`scripts/check_quality_gates.py` rejects lower/missing metrics, removal of per-file
enforcement, a narrowed source inventory and changes to the exclusion allowlist.
Its deliberate-fault tests cover each of those regressions.

## Backend and remaining repository work

The [application boundary pass](APPLICATION_BOUNDARY_COVERAGE.md) passes 2,266
locked PostGIS tests at exactly 100%: all 18,839 statements and 3,930 branch paths
across the package and handwritten migrations are covered. All 262 executable
backend Python files have independent 100% floors. The expanded frontend report passes 355
tests with 100% of every metric per file, including the owner map and build entry
points. Local pytest, Compose, shared CI and the per-report badge gates require
100%; policy tests reject narrowing either inventory.

The earlier [backend package completion](BACKEND_COMPLETE_COVERAGE.md) reached 100%
with 2,260 tests before migrations were added to its denominator.

The initial full PostGIS run on 2026-10-19 passed 1,492 tests at 91.36% combined
line/branch coverage. The added cases close application, SQL adapter, command,
provider, recovery, owner-console and worker failure paths. Protocol/type-only
declarations and ordinary coverage-tool exclusions remain non-executable scope.
No runtime module was removed to meet the target.

The [historical import command pass](IMPORT_COMMAND_COVERAGE.md) adds 19 cases
and enforces a 100% floor for all 223 statements and 50 branch paths in the
operator composition. Source preparation, lease/checkpoint ownership, provider
pauses, bounded media work and final verification remain source-free and resumable.
No runtime behavior or coverage exclusions change in this pass.
That combined PostGIS pass completed with 1,665 tests at 93.14% backend coverage.

The [backend domain pass](BACKEND_DOMAIN_COVERAGE.md) adds 57 failure-case tests.
All 20 domain implementations now measure 100% of their 1,739 statements and 420
branch paths, with independent 100% floors. That pass completed with 1,549 tests at
91.86% backend coverage. One documented exhaustive-enum fall-through is excluded
structurally, and the mapping test checks every enum member.

All 16 implementations in the catalog, contacts, estates and identity application
layers now have independent 100% combined line/branch floors. The added tests cover
well-formed but unsupported cursors, repeated filter bounds, invalid account states,
dummy-hash refusal and owner bootstrap collisions. See the
[public application evidence](PUBLIC_APPLICATION_COVERAGE.md). That pass completed
with 1,571 tests at 92.04% backend coverage. Remaining backend and operational
coverage work stays in scope. After that work reaches 100%, every
applicable global, per-file and badge threshold must also require 100%.

The [ingestion extraction/projection pass](INGESTION_PROJECTION_COVERAGE.md) adds
32 boundary cases and enforces 100% coverage for six implementations containing
818 statements and 282 branch paths. These cases assert currency/amount coherence,
source offsets, contact masking and preservation of protected replay values.
No new runtime exclusions or behavior changes are needed for this pass.
That combined PostGIS pass completed with 1,603 tests at 92.29% backend coverage.

Operational scripts already have their own `make quality-gates` tests and runtime
proofs, but those tests are not yet included in the application coverage reports.
Operational Python and shell coverage remain required before declaring the
repository-wide goal complete. An initial Python operations diagnostic measured
56.96% after excluding test/proof drivers; its remaining guards and transfer
behavior stay in scope. Measuring the existing release, topology and rollback
proofs raises that diagnostic to 65.10%; 1,505 lines and 630 branch paths remain
uncovered in the scoped operational Python report. Shell coverage remains open.

The [transfer operations pass](TRANSFER_OPERATIONS_COVERAGE.md) measures every
operational Python file through `coverage.operations.toml` and adds 31 transfer
cases. All 23 transfer implementations/entrypoints now cover their 1,231 statements
and 328 branch paths completely; these files and both coverage-policy checkers
have independent 100% floors in required Repository safety CI. `make quality-gates`
invokes `make coverage-operations`, and CI publishes its JSON report. Its source
inventory retains deployment helpers; test/proof drivers alone are omitted.
With the same existing release/topology/rollback proof drivers included, the
operational diagnostic rises to 72.54%; 1,198 lines and 482 branch paths remain
uncovered. The operations aggregate and remaining shell work still prevent
declaring the repository-wide goal complete.

The [activation/preflight pass](ACTIVATION_PREFLIGHT_COVERAGE.md) adds 25 cases for
host locks, environment/media pointer changes, failure restoration, identity sync,
HTTPS semantic probes and shared-edge admission. Both implementations cover all
428 statements and 132 branch paths; their independent 100% floors are enforced
alongside the completed transfer/quality-policy floors. Activation/preflight runtime source and
coverage exclusions remain unchanged in this pass. The comparable operational
diagnostic including the same existing proof drivers rises to 77.84%; 961 lines
and 395 branch paths remain uncovered.

The [release-evidence pass](RELEASE_EVIDENCE_COVERAGE.md) adds 20 cases for state,
source ordering, cache observation, truthful outcomes and bounded cohort evidence.
All six implementations cover 622 statements and 218 branch paths completely,
with independent 100% floors alongside the prior operational files. Two equivalent
simplifications remove exhaustive-command and already-validated timestamp guards;
the source inventory and exclusion allowlist remain unchanged. The comparable
operational diagnostic with the same proof drivers rises to 81.89%; 793 lines and
314 branch paths remain uncovered.

The [Dependabot evidence fix](DEPENDABOT_EVIDENCE_COVERAGE.md) adds 10 cases and an
independent 100% floor for all 290 statements and 128 branch paths in the controller.
It enforces the existing successful-check and bot-only policies: required checks
need explicit success, completed checks without results stay unverified, and
commit evidence must be nonempty with GitHub account identities. Git display names
provide no identity authorization. No runtime omission or coverage pragma is added.
The comparable audit with the same proof drivers rises to 83.86%; 717 lines and 268
branch paths remain uncovered.

The [shared-edge rollback/inventory fix](SHARED_EDGE_ROLLBACK_COVERAGE.md) adds
21 cases and independent 100% floors for release activation, inventory and staged
cutover: all 431 statements and 116 branch paths are covered. Same-release TLS and
redirect activation preserve the distinct rollback target; failed reloads restore
the prior configuration. Listener capture records TCP/UDP local addresses and
refuses malformed rows. Existing self-referential rollback state requires explicit
validated recovery, and both inventory snapshots must use the corrected collector.
The comparable audit with the same proof drivers rises to 89.02%; 485 lines and
188 branch paths remain uncovered. Operational Python, shell and substantive
embedded Python remain in scope.

The [production/candidate configuration pass](RELEASE_CONFIGURATION_COVERAGE.md)
adds 12 cases and independent 100% floors for both builders and validators: all
487 statements and 158 branch paths are covered. Assertions include private
non-overwriting env files, malformed/missing credentials, explicit provider and
recovery settings, source/path/image identity, loopback-only candidate verification
and internal database targeting. Runtime implementation and exclusions are unchanged.
The comparable audit with the same proof drivers rises to 92.89%; 317 lines and
119 branch paths remain uncovered.

The [release-artifact fallback fix](RELEASE_ARTIFACT_COVERAGE.md) adds eight cases
and independent 100% floors for checksums, manifest creation and verified reuse:
all 179 statements and 58 branch paths are covered. Explicit JSON object checks
route malformed manifest/image shapes into the existing full-verification fallback.
Checksum, source/fingerprint, immutable image and trusted-job requirements remain
unchanged; no runtime exclusion or dependency is added.
The comparable audit with the same proof drivers rises to 95.03%; 219 lines and
86 branch paths remain uncovered.

The [measured operational Python completion](OPERATIONS_COMPLETE_COVERAGE.md) adds
26 cases and closes all remaining file gaps: 355 operational tests cover all 4,694
statements and 1,456 branch paths. Global and all 54 per-file floors now require 100%.
It also fixes the reproduced redirect hostname-prefix/userinfo false positives by
parsing the HTTPS authority. Test/proof exclusions remain unchanged. Runtime shell
and substantive embedded Python remain in scope before completing the overall goal.

The [embedded deployment pass](EMBEDDED_DEPLOYMENT_COVERAGE.md) adds 13 cases and
moves the host collector and seven smoke contracts into measured helpers. Their
150 statements and 36 branch paths are fully covered without exclusions. It also
fixes semantic health failures being ignored inside a conditional shell function
and returns exhausted probes to the caller so automatic rollback can restore the
previous release. All 368 operational tests retain 100% globally and across the
expanded 56-file inventory. Remaining runtime shell coverage stays in scope.

The [runtime shell pass](RUNTIME_SHELL_COVERAGE.md) adds 17 behavioral cases and
eight Python report-gate tests. Failed application or worker startup now reaches
automatic rollback even inside the deployment conditional. All eleven shell files
require 100% lines, and all 376 operational Python tests retain 100% across the
expanded checker logic. No runtime exclusion is added.

The badge combines backend/frontend counters for display and independently requires
100% from each report. Operational Python and runtime shell independently require
100% in Repository safety; all four inventories must pass before merge.

Documentation, generated contracts/declarations, static assets, declarative
configuration, test fixtures and test/proof/browser drivers are excluded from
runtime measurement. This includes the synthetic Nginx fixture HTTP server,
architecture-violation driver, ESLint/PostCSS/test-runner configuration and OpenAPI
negative-probe shell driver. They retain their relevant formatting, link, build,
contract and integration checks. Workflow dependency wiring and primitive output
formatting are build/orchestration glue; substantive identity, authorization,
integrity and deployment logic remains in measured helpers. Existing narrow inline
exceptions retain their documented type/lifecycle/domain-invariant reasons; no
exception is added in the final shell pass.

The [ingestion orchestration pass](INGESTION_ORCHESTRATION_COVERAGE.md) adds 43
cases and independent 100% floors for seven implementations containing 620
statements and 134 branch paths. One documented branch exception follows the
domain invariant requiring every unassociated media result to carry a reason.
Import/recovery/worker failure cases remain executed and asserted.
That combined PostGIS pass completed with 1,646 tests at 92.55% backend coverage.

## Validation and review

Run `make coverage-frontend` for the locked Node container and the frontend gate;
`make coverage-backend` starts disposable PostGIS and runs all backend tests.
Run `make format-check lint typecheck test contract-check` before pushing the
coverage change, plus `make quality-gates` for policy drift and deliberate faults.
Reports remain ignored under `tmp/coverage/`; commit tests and policy rather than
generated reports. Coverage measures execution, so assertions and existing browser,
security, contract and runtime proofs remain necessary.
