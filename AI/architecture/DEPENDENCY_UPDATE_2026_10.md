# October 2026 dependency maintenance

The repository owner requested repair and merge of the open Dependabot updates
and a refresh to current stable packages on 2026-10-19. This is unplanned
maintenance; it does not introduce a product feature or a new production package.

## Security prerequisites

The Next.js security update keeps `next` and `eslint-config-next` at 16.3.8
and refreshes their locked image/source-map dependencies, including
`source-map-js` 1.2.2. The backend lockfile advances `urllib3` to its patched
release so both independent security audits can pass on the same PR. The
remaining Dependabot updates follow this common prerequisite.

No public API, database schema, environment, or deployment migration is needed.
Rollback is a squash-commit revert restoring the previous manifests and locks.
The usual format, lint, type, test, contract, image, browser, and audit gates
remain enforced.

## Vitest

The coupled `vitest` and `@vitest/coverage-v8` packages advance together to 5.0.5,
verified against npm on 2026-10-19. The full local suites still pass (1,464 backend
and 187 frontend tests); frontend coverage remains 96.01% lines and 90.07%
branches. The dependency lockfile is regenerated after integrating the shared
security prerequisite. No application behavior or coverage policy changes.
