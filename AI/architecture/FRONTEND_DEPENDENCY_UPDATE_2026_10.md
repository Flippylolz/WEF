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

## Main browser gate follow-up

Main release [39245886854](https://github.com/Flippylolz/WEF/actions/runs/39245886854)
failed in the WebKit account journey on `7946291`; deployment stopped before SSH,
leaving healthy production release `634b44f` active. The private journey exports
only masked screenshots, so the original assertion text is unavailable. Repeated
local execution of the unchanged application reproduced four runtime-guard
failures in 50 account journeys. Local-only exception metadata identified both a
viewport `?_rsc=...` request and catalog requests attempted during document reload.
A separate 20-run probe reproduced one offer click lost during viewport refresh.
These are bounded synthetic tests, not evidence of a production authentication or
data-loss incident.

Viewport replacements, URL normalization, and filter pushes previously used the
App Router's server navigation. The page's server component does not consume the
catalog search parameters: API queries already own that work. URL state now uses
`history.replaceState` and `history.pushState`, which Next integrates with
`useSearchParams` and back/forward navigation. This removes unnecessary RSC work
and its asynchronous route transitions while retaining backend-authoritative
filtering, shareable links, reload restoration, and the viewport debounce. See the
[Next.js SPA guidance](https://nextjs.org/docs/app/guides/single-page-applications#shallow-routing-on-the-client).

Unit regressions distinguish History API writes from server navigation. The
real-stack browser journey verifies filtered API responses, back/forward and
reload restoration, and absence of RSC requests during map/filter URL changes.
The account and detail journeys also wait for the initial viewport update and
successful completion of its map, listing, and uncertain-listing responses.
Otherwise a deliberate reload can start requests from an unloading document:
the History API change alone still reproduced one such guard failure in 50 runs.
Readiness evidence is reset for each new document; requests are never mocked.
The runtime-error guard, browser coverage, timeouts, and zero-retry policy remain
unchanged. No private diagnostic instrumentation or account payload is committed.

There is no dependency, API, database, or environment change. Roll back by
reverting the follow-up squash commit. A CI retry must still pass the exact-SHA
release gates before deployment; an Actions service outage is not authorization
to bypass them or deploy the candidate manually.

Local follow-up validation passes `make lint`, `make test` (1,468 backend and 191
frontend tests, including coverage gates), formatting, type and contract checks,
`make quality-gates` (196 script tests), Markdown links, and production runtime
image builds. The real-stack Chromium, WebKit, mobile Chrome, and mobile Safari
matrix passes 39 tests with nine existing profile-specific WebGL skips; the
desktop/mobile empty-state and date-filter browser suite passes all nine tests.
Local Firefox cannot launch its profile on this macOS host, so the required
Linux five-browser CI matrix remains mandatory. Bounded repeated-journey results
belong in the follow-up PR; raw local logs and generated reports remain excluded.
