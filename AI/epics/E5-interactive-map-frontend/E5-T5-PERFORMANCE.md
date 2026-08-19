# E5-T5 performance profile

Repeatable lab profile for the Warsaw Estate Finder map experience.

## Environment

- Production build served locally (`pnpm --filter web build && pnpm --filter web start`)
- Chromium mobile viewport: 390×844
- CPU: 4× slowdown
- Network: 1.6 Mbps down, 750 Kbps up, 150 ms RTT
- Dataset: deterministic synthetic M1 fixtures
- Tile/style bytes: stubbed at the network boundary (no CI dependency on public tile providers)

## Budgets (median of five cold-cache runs)

| Metric | Budget |
|--------|--------|
| First Contentful Paint (FCP) | ≤ 2.5 s |
| Largest Contentful Paint (LCP) | ≤ 4.0 s |
| Cumulative Layout Shift (CLS) | ≤ 0.10 |
| Total Blocking Time (TBT) | ≤ 300 ms |

## Implementation notes

- MapLibre is dynamically imported client-side; the map instance key remains stable across filter, viewport, selection, detail, and responsive transitions.
- Offer detail and media bundles load only after explicit offer selection (`fetchOfferDetail` is query-gated).
- Web Vitals collection uses a privacy-safe allowlist (metric name, value, rating, navigation type only) and is no-op without an explicit sink.

## Evidence recording

Record all five run values, tool versions, and the commit SHA when validating this profile locally. CI does not gate on external tile latency; regression coverage relies on unit/browser tests for lifecycle, deferred detail fetch, and web-vitals payload allowlists.
