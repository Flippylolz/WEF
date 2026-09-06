---
schema: ai-workflow/task@1
id: E14-T5
epic: E14
title: "Add full-stack cross-browser and accessibility journeys"
status: in_progress
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E14-T3, E14-T4]
requirement_ids: [P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008]
decision_ids: [ADR-004, ADR-011, ADR-013, ADR-016]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  source: ../proposed-tasks/E14-T5-add-full-stack-cross-browser-and-accessibility-journeys.md
  promoted_by: "Codex agent (owner-approved E14 planning under AD-041)"
  promoted_at: "2026-08-29T21:17:35Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent (AD-041)"
  verified_at: "2026-08-29T21:17:35Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-06T06:51:36.365914+00:00"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-06T08:08:28.800204+00:00"
  evidence: ["E14-T3 done via PR #360, merge 88aaa5c1467b66323d531786548e1033814d9a23", "E14-T4 done via PR #361, merge a786d6b785253a3413ed5d338a443ba917fb5a70; release 34021148552 succeeded"]
branch:
  required: true
  name: feat/E14-T5-real-stack-browser
  task_id: E14-T5
  one_task_only: true
  created_at: "2026-09-06T08:08:28.800204+00:00"
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
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

- [x] Critical journeys fail if migrations, generated contracts, API routing, cookies/CSRF, persistence, or frontend wiring are broken.
- [x] Chromium/Firefox/WebKit desktop and approved mobile projects pass; any reduced CI matrix has documented risk and a scheduled/full matrix.
- [x] A real WebGL Chromium journey proves map initialization and pin/list selection; fallback remains usable without WebGL.
- [x] Keyboard-only flows and axe checks cover every critical interactive surface with zero unreviewed serious/critical violations.
- [x] Fixtures and artifacts contain only synthetic/redacted values; contact/session/secret leakage scans pass.
- [x] Failures upload bounded trace/screenshot evidence and do not expose secrets.
- [x] Full-stack build/migration/seed, browser matrix, axe, keyboard, contract, and artifact-safety checks pass.

## Dependencies and gates

Depends on E14-T3 and E14-T4 so stable seams are tested end to end.

## Risks and notes

Separate product defects from browser-infrastructure flakes. A retry may collect evidence
but cannot convert a reproducible first-attempt defect into success.

## Ready checklist

- [x] E14 spike revision 1 is owner-approved under AD-041.
- [x] The task was moved to `tasks/` with complete promotion metadata.
- [x] E14 implementation plan revision 1 is owner-approved and E14-T3/T4 are done.

## Start evidence

Moved through ready before implementation under scoped owner approval for T1–T5.
Started on the exact open T4 ancestor above; no completion/merge until T4 is done.
Full-stack fixtures use an isolated test-only database and internal network.

## Local verification

See [T5 verification](../T5_VERIFICATION.md) for the fresh-stack matrix, canonical
checks, discovered defects and privacy boundaries. Local acceptance is verified;
current-head CI and merge remain required before task completion.
