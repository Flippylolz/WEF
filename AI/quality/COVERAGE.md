# Coverage scope and progress

The owner requested 100% code coverage on 2026-10-19, excluding documentation and
other files without application behavior. This is unplanned quality maintenance
under that direct request. Application behavior, API contracts, schema, providers
and production deployment configuration remain within their existing boundaries.

## Frontend gate

Vitest measures every `src/**/*.{ts,tsx}` file, including files never imported by
tests. Lines, branches, functions and statements each require 100%, independently
for every file. Next.js entry points, middleware, error documents, translation
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

The initial full PostGIS run on 2026-10-19 passed 1,492 tests at 91.36% combined
line/branch coverage. Backend code has not reached 100%; its 90% gate and existing
critical-module floors remain active while genuine missing behavior is covered.
SQL adapters, operator commands and external-provider error paths stay in scope.
Protocol/type-only declarations and ordinary coverage-tool exclusions remain
non-executable exclusions rather than tests of type declarations.

Operational scripts already have their own `make quality-gates` tests and runtime
proofs, but those tests are not yet included in the application coverage reports.
Their coverage inventory, backend-owned admin JavaScript and the backend gaps must
also be addressed before declaring the repository-wide goal complete.

The badge combines backend/frontend counters for display. It is not evidence that
the repository goal is complete: the backend remains below 100%, and the badge's
90% per-report minimum is supplemented by the stricter frontend job and critical
file checks.

## Validation and review

Run `make coverage-frontend` for the locked Node container and the frontend gate;
`make coverage-backend` starts disposable PostGIS and runs all backend tests.
Run `make format-check lint typecheck test contract-check` before pushing the
coverage change, plus `make quality-gates` for policy drift and deliberate faults.
Reports remain ignored under `tmp/coverage/`; commit tests and policy rather than
generated reports. Coverage measures execution, so assertions and existing browser,
security, contract and runtime proofs remain necessary.
