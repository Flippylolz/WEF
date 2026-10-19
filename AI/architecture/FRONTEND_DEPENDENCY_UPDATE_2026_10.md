# October 2026 frontend stable dependency refresh

This is unplanned maintenance requested by the repository owner alongside the
open Dependabot PR repairs. npm's stable releases were checked on 2026-10-19.
The frontend refresh includes Next.js/ESLint config 16.4.2, React/React DOM 19.3.1,
MapLibre 6.15.0, React Query 5.104.4, next-intl 4.14.9, React Hook Form 7.90.0,
Zod 4.6.7, Playwright 1.64.1, Redocly 2.64.1, and current compatible tooling and
transitive dependencies. The existing ESLint React-version workaround matches
React 19.3.1. Vitest remains a separate coupled update; the resolver major upgrade
is reviewed separately from routine updates.

The full local suites pass: 1,468 backend tests and 191 frontend tests. Frontend
coverage remains 96.16% lines / 90.04% branches. A Node 22.23.3 production build
measures 570,497 gzip bytes across all 16 JavaScript chunks, below the unchanged
599,617-byte budget.
The explicitly requested MapLibre 6.15.0 stable release was published less than
24 hours before this audit. Its exact-version pnpm age exception is recorded in
`pnpm-workspace.yaml`; other supply-chain policies are unchanged. The release
was verified against the upstream GitHub release and npm metadata. The production dependency audit reports no vulnerabilities.
Formatting, lint, type, and contract checks also pass. Current-head CI additionally
verifies all real-stack browsers and runtime images before merge.

There is no API, schema, environment, or database migration. Upstream rendering,
form, map, and build compatibility are covered by the existing suites and browser
gates. Rollback is a squash-commit revert restoring manifests, lockfile, and the
matching lint setting.

## Unpublished development-only advisory fix

The complete development audit reports GHSA-vfj7-8cjw-p6xm in braces 3.0.3.
npm still publishes 3.0.3 as the latest release; 3.0.4 does not exist in the
registry, and the [upstream advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
lists no patched version. The issue is confined to development tooling in this
lockfile; the production audit is clean. No audit-ignore rule or fictional
package version is committed. A future published fix remains a dependency update.

## MapLibre worker deployment compatibility

MapLibre 6.15 bundles its worker independently instead of importing the shared
module. The deployment smoke validator accepts either the existing shared-module
import or a bundled worker with the standard worker message APIs. It retains
JavaScript MIME and HTML-fallback rejection checks, and requires shared-module
exports only when the worker imports that module. The new self-contained worker
ships an empty, unused shared-module stub.
Regression tests cover both valid layouts and malformed/MIME/fallback failures;
the real production runtime proof still exercises the served assets.

Cold-start runtime validation also reproduced a PostGIS init race: its temporary
Unix socket passed the old readiness check before TCP was available to migrations.
Local, production, and CI database health checks now use loopback TCP, matching
the existing browser-test stack. The runtime proof explicitly checks TCP after
both initial creation and persistence recreation before starting client services.

Final validation also includes the concurrent catalog hotfix #409.
