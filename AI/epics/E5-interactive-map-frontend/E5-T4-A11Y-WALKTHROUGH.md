# E5-T4 accessibility walkthrough record

Recorded by Cursor Agent (autonomous epic mission) on 2026-08-19 after E5-T3 merged.

## Desktop (≥ 1024 px)

- Tab order: account toolbar → filter controls → location list → offer actions → detail drawer close.
- Location list hover/focus highlights the corresponding map pin without requiring canvas interaction.
- Sidebar collapse/expand preserves filters and URL state; focus returns to the floating reopen control.
- Offer detail drawer opens from explicit action, traps focus while open, restores focus on Escape/close.
- Verified Telegram links expose `noopener noreferrer` and HTTPS-only hrefs.

## Mobile (360 px)

- Map-first layout shows a bottom results bar with location count.
- Bottom sheet opens for filters/results; full-list mode covers the viewport; “Show map” returns to map-first mode.
- No horizontal overflow observed at 360 px width in component tests and CSS breakpoints.
- Touch targets for mobile results bar and panel toolbar meet minimum sizing via padded pill buttons.

## Degraded states

- Map tile/style failure keeps the semantic location list and filter controls mounted.
- API errors announce through `role="alert"` or `role="status"` without exposing raw payloads.
- Loading states use status regions; background refetches do not move keyboard focus.

## Automated checks

- `vitest-axe` runs against the rendered map explorer shell in `map-explorer.a11y.test.tsx`.
- Repository CI runs `make lint`, `make typecheck`, and `make test` including the new accessibility suite.

## Reduced motion

- `@media (prefers-reduced-motion: reduce)` disables sidebar, drawer, and gallery transitions.
- Map cluster expansion uses zero duration when reduced motion is preferred.
