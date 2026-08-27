---
schema: ai-workflow/proposed-task@1
id: E14-T5
epic: E14
title: "Add full-stack cross-browser and accessibility journeys"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E14-T3, E14-T4]
requirement_ids: [P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008]
decision_ids: [ADR-004, ADR-011, ADR-013, ADR-016]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E14-T5: Add full-stack cross-browser and accessibility journeys

## Outcome

Required browser tests exercise the built web app, real FastAPI service, migrations,
and disposable PostGIS using synthetic data across the supported browser/device matrix,
including real map initialization and restricted-account journeys.

## Scope

- Add a disposable full-stack E2E topology with deterministic synthetic seed and no route mocks for critical journeys.
- Cover search/filter/share URL, map/list/detail/media, registration/login/password change, contact reveal, favorites, logout, error recovery, and release identity.
- Run Chromium, Firefox, and WebKit desktop projects plus a risk-based mobile Chrome/Safari-emulation subset.
- Keep at least one WebGL-enabled Chromium map/pin smoke; retain a map-disabled fallback journey separately.
- Add browser-level axe and keyboard/focus checks for explorer, filters, drawers, gallery, auth, contact reveal, favorites, errors, and mobile panels.
- Preserve traces/screenshots/videos only on failure under bounded artifact retention.

## Out of scope

- Live Telegram/provider calls, production data assertions, visual redesign, exhaustive browser/version combinations, or using retries to hide deterministic failures.

## Acceptance criteria and checks

- [ ] Critical journeys fail if migrations, generated contracts, API routing, cookies/CSRF, persistence, or frontend wiring are broken.
- [ ] Chromium/Firefox/WebKit desktop and approved mobile projects pass; any reduced CI matrix has documented risk and a scheduled/full matrix.
- [ ] A real WebGL Chromium journey proves map initialization and pin/list selection; fallback remains usable without WebGL.
- [ ] Keyboard-only flows and axe checks cover every critical interactive surface with zero unreviewed serious/critical violations.
- [ ] Fixtures and artifacts contain only synthetic/redacted values; contact/session/secret leakage scans pass.
- [ ] Failures upload bounded trace/screenshot evidence and do not expose secrets.
- [ ] Full-stack build/migration/seed, browser matrix, axe, keyboard, contract, and artifact-safety checks pass.

## Dependencies and gates

Depends on E14-T3 and E14-T4 so stable seams are tested end to end.

## Risks and notes

Separate product defects from browser-infrastructure flakes. A retry may collect evidence
but cannot convert a reproducible first-attempt defect into success.

## Promotion checklist

- [ ] E14 spike is explicitly owner-approved at its current revision.
- [ ] Scope, checks, dependencies, priority/size, and traceability match the approved spike.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.
