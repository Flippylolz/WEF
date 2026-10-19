# October 2026 frontend stable dependency refresh

This is unplanned maintenance requested by the repository owner alongside the
open Dependabot PR repairs. npm's stable releases were checked on 2026-10-19.
The frontend refresh includes Next.js/ESLint config 16.4.2, React/React DOM 19.3.1,
MapLibre 6.15.0, React Query 5.104.4, next-intl 4.14.9, React Hook Form 7.90.0,
Zod 4.6.7, Playwright 1.64.1, Redocly 2.64.1, and current compatible tooling and
transitive dependencies. The existing ESLint React-version workaround matches
React 19.3.1. Vitest remains a separate coupled update; the resolver major upgrade
is reviewed separately from routine updates.

The full local suites pass: 1,464 backend tests and 187 frontend tests. Frontend
coverage remains 94.75% lines / 90.07% branches. A Node 22.23.3 production build
measures 563,982 gzip bytes across all 16 JavaScript chunks, below the unchanged
599,617-byte budget. The production dependency audit reports no vulnerabilities.
Formatting, lint, type, and contract checks also pass. Current-head CI additionally
verifies all real-stack browsers and runtime images before merge.

There is no API, schema, environment, or database migration. Upstream rendering,
form, map, and build compatibility are covered by the existing suites and browser
gates. Rollback is a squash-commit revert restoring manifests, lockfile, and the
matching lint setting.
