# E14-T3 frontend orchestration verification

## State and behavior ownership

The original 170-test suite passed before extraction on T2 head
`f1f46fb4be6811232763f1b2c9b1d57218e3b3d1`; the same behavior assertions pass after
extraction. Tests now group navigation, selection, list recovery, credentials,
password changes, sessions, detail lifecycle, presentation and contacts separately.
Shared synthetic fixtures/mock setup are excluded from production coverage using
`coverageConfigDefaults` plus only the `.test-support.tsx` suffix; production files
remain measured. No assertions were removed. Two new keyboard/axe checks pass.

| Seam | Owner and boundary |
| --- | --- |
| `use-map-navigation` | Canonical URL serialization, history mode, viewport debounce/cancellation and filter navigation; existing URL library remains authoritative |
| `use-map-catalog` | TanStack catalog/facet/list queries, retained safe list on refresh error, one-page prefetch and server cursor |
| `use-map-selection` | Selected IDs, feature snapshot, map focus target, responsive panel state, return trigger/scroll restoration |
| `use-explorer-account` | Server account, visit and favorites queries; browser visit fallback and favorite invalidation |
| `offer-panel` | Backend offer summary presentation and explicit selection callback |
| Account forms / signed-in panel | Credential form submission vs session/account actions; modal owns native dialog lifecycle |
| Detail content / contact reveal | Backend projection rendering vs explicit private reveal request; drawer owns loading/error and focus lifecycle |

Generated DTOs, query keys, cancellation signals, stale data behavior and backend
policy authority are preserved. No new client store, runtime dependency, parser
rule, public API or schema. Account API responses remain authoritative. The drawer's
wrapper changed from `aside` to `div`: axe rejects `role="dialog"` on `aside`; CSS,
labels, keyboard close and focus restoration are unchanged.

## Regression budgets

Each function in extracted explorer hooks has an ESLint cyclomatic-complexity ceiling
of 12 (fatal). The composing map JSX and presentation/form components are explicitly
outside that ceiling: their parallel rendering branches are not query/state policy,
and flattening those branches only to meet a number would obscure their behavior.
Future policy/state additions belong in the typed owners above, with characterization
coverage. `check-frontend-boundaries.mjs` parses static imports/re-exports and literal
dynamic imports using the existing TypeScript development dependency, then rejects
cycles throughout source modules. A deliberate self-import was rejected.

Every production build checks all JavaScript in `.next/static/chunks`, including
lazy chunks. This conservative whole-app bound includes the route's shipped JS.
Baseline at the exact T2 head: 563,637 gzip bytes, 17 chunks. T3: 566,220 bytes,
17 chunks (+2,583 bytes, 0.46%). Compression uses gzip level 9 in both measurements.
The checked-in 569,273-byte ceiling allows 1% growth; exceeding it requires an
explained budget update in a reviewed change. A deliberately one-byte ceiling failed.
This is a transfer-size regression signal, not a runtime-performance claim.

## Validation and limits

Frontend lint, strict type check, coverage (172 tests), axe and production build pass.
Global lines/branches: 95.82% / 90.22%; independent auth/URL floors remain enforced.
Existing tests still cover URL round-trips, cancellation, no eager offer requests,
map/list selection, favorites, auth/contact failures, stale-list retry and drawer
Escape/return focus. Final canonical `make verify` and required PR CI are recorded
in the task PR. Real browser dialog focus, WebGL, cross-browser/mobile journeys and
real API/PostGIS browser integration remain E14-T5 acceptance, not claimed here.

Rollback uses the prior image/commit; no product data or database changes.
