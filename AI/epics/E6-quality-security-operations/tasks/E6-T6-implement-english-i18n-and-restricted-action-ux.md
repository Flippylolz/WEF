---
schema: ai-workflow/task@1
id: E6-T6
epic: E6
title: "Implement English i18n and restricted-action UX"
status: ready
revision: 1
priority: P1
size: L
milestone: M3
dependencies: [E5-T3, E6-T4, E6-T5]
requirement_ids: [P-002, P-008]
decision_ids: [ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T11:27:24Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T11:27:24Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 4
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T11:27:24Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T11:27:24Z"
  evidence:
    - "E5-T3 | done | offer detail drawer on main"
    - "E6-T4 | done | identity sessions (PR #51)"
    - "E6-T5 | done | contact reveal API (PR #110)"
branch:
  required: true
  name: feat/E6-T6-restricted-action-ux
  task_id: E6-T6
  one_task_only: true
  created_at: null
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

# E6-T6: Implement English i18n and restricted-action UX

## Outcome

English i18n-keyed auth and restricted-action UX exists so anonymous users browse freely while register/login/password-change/session controls and explicit contact reveal are available through accessible flows that return to the selected offer after sign-in.

## Scope

- Extend the existing E9 account modal with password change (including forced `must_change_password`) and session revocation.
- Add offer-detail contact reveal: explicit click only; anonymous users open sign-in with return-to-offer; revealed values stay in memory and are not prefetched, persisted, or query-cached.
- Keep user-facing auth/reveal/error strings in English message catalogs; avoid new hardcoded copy in components.
- Vitest coverage for the new flows (including rate-limit/forbidden/unavailable presentation).

## Out of scope

- Owner administration console (E6-T7).
- Production HTTPS enablement of registration/reveal (E7-T7).
- Additional locales beyond English keys.

## Affected modules and contracts

- `apps/web/src/components/account-modal.tsx`, `user-toolbar.tsx`, `offer-detail-drawer.tsx`, `map-explorer.tsx` (wiring), `lib/auth-api.ts`, new contacts client, `messages/en.json`, tests.

## Acceptance criteria

- [ ] Components contain no new hardcoded user-facing copy outside reviewed catalogs.
- [ ] Anonymous users can browse everything except restricted actions.
- [ ] Reveal requires explicit click; successful values are not prefetched, persisted, or cached.
- [ ] Keyboard/accessibility/error/rate-limit flows pass tests.
- [ ] Forced-password-change users cannot reveal until password is changed.

## Rollback

Redeploy previous web image; no database migration.
