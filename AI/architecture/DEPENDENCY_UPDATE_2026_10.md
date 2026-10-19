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
