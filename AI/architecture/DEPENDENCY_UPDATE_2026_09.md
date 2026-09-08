# September 2026 frontend dependency update

This is unplanned dependency maintenance requested by the repository owner,
tracked in PR #381 (Dependabot replaced #374 after regrouping updates). No API, schema, environment, or deployment migration is needed.

The runtime updates are unchanged from #374; #381 additionally refreshes
Playwright, ESLint, and Redocly development tooling.

The complete locked patch/minor update produces 593,735 gzip bytes in production
JavaScript, compared with 567,719 bytes for the current application with its
previous runtime dependencies (26,016 bytes / 4.58% growth). Both measurements use
Node 22.22.2 and the existing level-9 gzip checker over every production chunk,
including lazy chunks. CI independently measured the same 593,735-byte update.

Controlled builds with MapLibre 6.6.0 produce 587,049 bytes; additionally restoring
Next.js 16.3.3 produces 586,994 bytes. The remaining increase is in the application
dependency chunk. Restoring react-map-gl 8.1.2 alone increases the update to
594,982 bytes, so reverting that wrapper would not recover the budget.

Accept the bounded dependency cost and rebaseline `frontend-budgets.json` to the
reviewed Dependabot head, preserving the existing 1% growth allowance: the new
limit is 599,672 bytes. The checker still measures all production JavaScript and
fails above that limit. No runtime code or coverage threshold is relaxed.
Future application growth remains subject to this limit. Rollback is the PR's
squash revert, restoring both the prior lockfile and prior budget.
