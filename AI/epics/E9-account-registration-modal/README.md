---
schema: ai-workflow/epic@1
id: E9
title: "Account registration modal"
status: ready
milestones: [M3]
owner: owner
---

# E9: Account registration modal

## Outcome

Anonymous visitors can create an account and sign in through an accessible modal dialog. No separate profile page is introduced; authenticated users manage their session from the same modal.

## Approval state

- Epic workspace status: `ready`; owner-authorized implementation of the registration modal UX against the existing E6-T4 identity backend.
- Form validation uses `react-hook-form` with `zod` resolvers, matching the architecture spike recommendation.
- Modal presentation uses the native `<dialog>` element to avoid an additional UI framework dependency.

## Milestones

[M3](../../milestones/M3-public-dockerized-mvp.md)

## Governing domain documents

- [Product](../../product/README.md)
- [Security — auth](../../security/AUTH_ADMIN_CONTACTS.md)
- [Architecture](../../architecture/README.md)

## Governing decisions

- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)

## Promoted tasks

- [E9-T1: Implement account registration modal](tasks/E9-T1-implement-account-registration-modal.md) — `done`, P1/M, M3

## Dependencies

- [E6-T4](../E6-quality-security-operations/tasks/E6-T4-implement-in-house-registration-and-sessions.md) — backend registration and session APIs
