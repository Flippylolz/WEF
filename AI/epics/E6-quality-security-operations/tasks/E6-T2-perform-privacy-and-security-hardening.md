---
schema: ai-workflow/task@1
id: E6-T2
epic: E6
title: "Perform privacy and security hardening"
status: in_progress
revision: 1
priority: P1
size: M
milestone: M3
dependencies: [E3-T4, E4-T3, E5-T3]
requirement_ids: [P-002, P-005, P-006, P-007, P-008]
decision_ids: [ADR-007, ADR-011, ADR-013, ADR-016]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E6-T2-perform-privacy-and-security-hardening.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T16:17:08Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T16:17:08Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 6
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T16:17:08Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T16:17:08Z"
  evidence:
    - "E3-T4 | done | media storage/derivatives"
    - "E4-T3 | done | offer detail"
    - "E5-T3 | done | offer detail/media gallery"
branch:
  required: true
  name: feat/E6-T2-privacy-security-hardening
  task_id: E6-T2
  one_task_only: true
  created_at: "2026-08-20T16:17:08Z"
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

# E6-T2: Perform privacy and security hardening

## Outcome

Close residual privacy and security gaps on the live HTTPS WEF origin after E7-T10/E7-T7/E7-T11: HSTS, docs/OpenAPI denial, safe media delivery, contact non-disclosure for anonymous clients, public-field honesty, and dependency-scan evidence.

## Scope

- Enable `Strict-Transport-Security` on the shared Nginx HTTPS WEF vhost (post-verified certs).
- Prove production `/docs`, `/redoc`, and OpenAPI routes remain 404; runtime images stay free of docs generators.
- Confirm anonymous clients cannot retrieve raw phone/contact data; reveal stays authenticated/rate-limited/audited.
- Confirm media edge refuses dotfiles/path traversal; restricted originals stay unpublished.
- Refresh public UX copy that falsely claims all records are synthetic after historical activation.
- Record CI advisory-scan status (pip-audit / pnpm audit) with explicit acceptance if any high findings remain.

## Out of scope

- E6-T1 Playwright/accessibility pyramid, E6-T3 operational diagnostics, bulk visibility promotion, Forecast TLS, backups (E7-T5), Telegram (E8).

## Work

- Update shared-edge TLS templates and topology proofs; apply/reload on NUC.
- Add or extend regression coverage for headers/docs/media privacy boundaries.
- Adjust English public subtitle/copy for post-activation honesty.

## Acceptance criteria

- [ ] Production clients cannot access raw payloads, file paths, secrets, database, or worker through the public edge.
- [ ] Production returns 404 for OpenAPI/Swagger UI/ReDoc routes and runtime images contain no documentation generators/assets.
- [ ] Anonymous clients cannot retrieve raw phone/contact data; authenticated reveal follows AUTH_ADMIN_CONTACTS.
- [ ] HTTPS responses include HSTS plus existing CSP/Referrer-Policy/X-Content-Type-Options/X-Frame-Options.
- [ ] High-severity dependency findings are resolved or explicitly accepted in task evidence.
- [ ] Public marketing copy no longer claims the catalog is synthetic-only after historical activation.

## Dependencies and gates

- Dependencies: E3-T4, E4-T3, E5-T3 (`done`).
- Implementation plan revision 6 authorizes this task.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).

## Risks and notes

- HSTS is sticky for browsers; keep max-age bounded and omit `preload` unless separately approved.
- Do not put HSTS on plain `:3100` Caddy rollback.
- Material auth/contact model changes require spike revalidation.

## Rollback

Redeploy previous shared-edge release without HSTS; revert public copy strings with a prior web image if needed.
