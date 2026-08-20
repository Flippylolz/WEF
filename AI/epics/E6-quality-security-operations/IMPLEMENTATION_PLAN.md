---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Quality, security, and operations implementation plan"
status: approved
revision: 4
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T6
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T11:27:24Z"
  approved_revision: 4
  evidence: "Owner continue / autonomous epic mission (AD-009); E5-T3/E6-T4/E6-T5 done on main; E9 registration modal already present—E6-T6 completes password/session/reveal UX and i18n"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: E6-T6 English i18n and restricted-action UX

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved.
- Binding docs: [AUTH_ADMIN_CONTACTS](../../security/AUTH_ADMIN_CONTACTS.md), ADR-011/012/016.
- E9-T1 already delivered register/login modal; this plan sequences only the remaining E6-T6 acceptance surface.

## Scope and outcome

Complete restricted-action frontend UX: password change (including forced `must_change_password`), session revocation, English i18n for auth/reveal/error strings, and an explicit audited contact-reveal control on offer detail with return-to-offer after anonymous sign-in. No production auth enablement (E7-T7).

## Ordered task sequence

1. [E6-T6: Implement English i18n and restricted-action UX](tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md) — revision 1.
   - Independently reviewable: web-only (plus message catalogs); reuses existing OpenAPI `revealOfferContacts` / auth password/session paths.
   - Dependencies: E5-T3, E6-T4, E6-T5 — all `done`.
   - Affected modules: `apps/web` account modal/toolbar, offer detail drawer, auth/contacts API clients, `messages/en.json`, vitest coverage.
   - Tests: reveal requires click; anonymous opens sign-in and returns to offer; must_change blocks reveal; rate-limit/error states; no revealed plaintext in query cache; a11y smoke for new controls.
   - Out of scope: Starlette Admin (E6-T7), HTTPS activation (E7-T7).

Only E6-T6 is sequenced. E6-T7 remains proposed until a later plan revision.

## Cross-task architecture

- Reveal plaintext stays in component memory only (`useState`); never `react-query` cache or `localStorage`.
- API calls use `cache: "no-store"`; backend already sends `Cache-Control: no-store, private`.
- Lift or share a thin auth-UI intent so offer detail can request login/register with return focus on the same offer.

## Security and privacy

- Do not prefetch reveal on drawer open or hover.
- Forced-password-change users are directed only to password change/logout.
- Prefer generic client messages; do not surface raw backend contact material in error text.

## Test and verification strategy

- Vitest component tests; existing web typecheck/lint/build CI gates.
- No backend contract change expected; if OpenAPI untouched, skip contract regen.

## Operations, rollout, and rollback

- Frontend image redeploy; no migration.
- Feature remains inert on plain HTTP until E7-T7 enables auth in production.

## Risks and mitigations

- Scope creep into owner console: explicitly out of scope.
- Duplicate auth modal ownership with E9: extend existing `AccountModal`/`UserToolbar` rather than a second stack.

## Invalidation triggers

- Material change to reveal authorization or public auth contracts.
- Requirement to ship a second locale (beyond English keys) in this task.

## Approval checklist

- [x] Spike revision approved and valid.
- [x] Sequence entries are promoted tasks with acceptance criteria.
- [x] Dependencies complete.
- [x] Modules, tests, risks, rollback explicit.
- [x] No deferred decisions for this slice.
- [x] Approval under continue / AD-009.
