---
schema: ai-workflow/task@1
id: E9-T1
epic: E9
title: "Implement account registration modal"
status: done
revision: 1
priority: P1
size: M
milestone: M3
dependencies: [E6-T4]
requirement_ids: [P-008]
decision_ids: [ADR-012, ADR-016]
deferred_decision_ids: []
branch:
  required: true
  name: feat/E9-T1-account-registration-modal
  task_id: E9-T1
  one_task_only: true
---

# E9-T1: Implement account registration modal

## Outcome

Visitors can register, log in, and log out through a modal with validated editable fields. The backend remains authoritative; the frontend uses generated OpenAPI types and session cookies.

## Scope

- Add `react-hook-form`, `zod`, and `@hookform/resolvers` for immediate client-side validation aligned with backend rules.
- Native `<dialog>` modal with register and login modes; no dedicated profile route.
- Fixed account toolbar button opening the modal; authenticated users see their username and can log out.
- Typed auth API client with `credentials: "include"` for HttpOnly session cookies.
- English i18n keys for all user-visible auth copy.
- Component and API client tests.

## Out of scope

- Password change, account disable/delete, or owner administration.
- Contact reveal or restricted-action flows (E6-T5/E6-T6).

## Acceptance criteria

- [x] Register creates an account via `POST /api/v1/auth/register` with field-level validation feedback.
- [x] Login establishes a session and updates toolbar state via `GET /api/v1/auth/me`.
- [x] Logout clears the session cookie and returns to anonymous browsing.
- [x] Modal is keyboard-accessible with focus trap behavior from the native dialog.
- [x] Lint, typecheck, tests, and contract checks pass.
