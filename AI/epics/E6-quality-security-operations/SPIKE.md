---
schema: ai-workflow/spike@1
epic: E6
title: "Quality, security, and operations research"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-007, ADR-008, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014, ADR-015, ADR-016]
domain_docs: [product, security, operations, governance, contracts]
proposed_task_ids: [E6-T1, E6-T2, E6-T3, E6-T4, E6-T5, E6-T6, E6-T7]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-14T11:46:36Z"
  approved_revision: 2
  evidence: "Spike PR https://github.com/Flippylolz/WEF/pull/49 merged after green CI (squash cd2ad36) under the owner's 2026-08-14 session directive to take E6, document the spike, and proceed through stacked PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Quality, security, and operations

> This spike authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

What cross-cutting test, privacy, security, identity, contact-reveal, administration, localization, and operational controls are required for a safe public launch, and which E6 work is actionable now versus gated behind incomplete E3/E4/E5 tasks?

## Context and constraints

- Anonymous browsing remains available; pseudonymous username/password accounts gate only restricted actions.
- Contacts are extracted and encrypted at rest, masked server-side, explicitly revealed through a no-store audited endpoint, and never logged in reveal audits.
- The fixed owner role alone administers users/sessions/resets/audits through owner-authorized interactors; generic admin forms cannot expose sensitive fields.
- Authentication/admin/reveal remain disabled on plain HTTP and require production HTTPS/secrets.
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md) fixes pseudonymous username/password accounts (no email) and a fixed owner role; [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md) fixes audited contact reveal behind accounts.
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md) keeps backups deferred; no E6 task may introduce backup/recovery claims.
- The catalog schema persists no accounts, sessions, audits, or contact ciphertext today; all identity/contact-reveal persistence is new schema under E6-T4/E6-T5.

Governing domains:

- [Product](../../product/README.md)
- [Security](../../security/README.md)
- [Operations](../../operations/README.md)
- [Governance](../../governance/README.md)
- [Contracts](../../contracts/README.md)

Governing decisions and deferred gates:

- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-014](../../decisions/adr/ADR-014-actions-owned-deploy-configuration.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)

No E6 proposed task carries an unresolved `deferred_decision_ids` gate; D-002/D-009 gate E3/E7 work only.

## Research method

- Full read-only repository survey (2026-08-14) of `apps/backend`, `apps/web`, `contracts/`, `infra/`, `scripts/`, and `.github/workflows/` for test layers, security posture, diagnostics, structure, i18n, and contract tooling.
- Review of the governing domain documents and the locked [E0 architecture proof](../E0-architecture-dependency-spike/PROOF_REPORT.md).
- Dependency-graph analysis of every E6 proposed task against the current done/proposed state of E1–E5 recorded in the [epics index](../README.md).

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline (repository survey, 2026-08-14)

Test pyramid:

- Backend: pytest with `asyncio_mode=auto`, coverage `fail_under=90` with branch coverage, 18 test files / 100 test functions across unit, HTTP-with-fakes, and `pytest.mark.integration` layers against disposable PostGIS (`apps/backend/tests/`).
- Frontend: Vitest + Testing Library, jsdom, 6 colocated test files (URL lifecycle, components, request lifecycle).
- CI (`.github/workflows/ci.yml`) already enforces ruff, strict mypy, import-linter plus an architecture-violation probe, pytest+coverage, deterministic OpenAPI export diff, contract codegen/lint/docs checks, oasdiff breaking-change detection with a negative probe, prettier/eslint/tsc/vitest, `next build`, pip-audit, `pnpm audit --prod`, secret/source-exclusion assertions, compose validation, and runtime-image proofs (non-root, no dev tooling).
- Confirmed gaps: no browser/e2e tests (no Playwright/Cypress anywhere), no accessibility test tooling, no load/performance tests, no Dependabot configuration (E1-T6/T7 remain proposed).

Security and privacy:

- No auth/session/identity infrastructure exists: no users/session/audit tables, no cookies, no password hashing; only unrelated `AsyncSession` matches.
- Contact extraction exists only in the read-only ingestion boundary (`ContactSpan` phone/telegram spans); the aggregate dry-run report is deliberately contact-free.
- `OfferRow.source_text_public_masked` currently copies the excerpt verbatim in the M1 synthetic seed adapter (`apps/backend/src/wef_backend/features/catalog/infrastructure/seed_adapter.py`): no production masking logic exists yet.
- No rate limiting, no CORS middleware, no CSRF/origin checks; the only middleware attaches an `X-Request-ID`. Security headers exist only at the production edge (`infra/Caddyfile.production`).
- Secrets remain GitHub-Actions-owned (ADR-014); CI asserts absence of `.env`, source exports, and key/session files.

Operational diagnostics:

- Health: `GET /api/v1/health/live` and `/ready`; readiness also verifies `alembic_version == EXPECTED_DATABASE_REVISION`.
- structlog is a dependency and used ad hoc, but is never configured; there is no request-access logging and no metrics/tracing.

Structure:

- Backend: FastAPI modular monolith with import-linter layer contracts (domain/application layers cannot import fastapi/sqlalchemy/pydantic); features `catalog`, `estates` (retired stub), `ingestion`; SQLAlchemy 2.0 async + Alembic with two migrations.
- Frontend: Next.js 16 App Router, React 19, TanStack Query, maplibre; single explorer surface with no detail route and no auth components.
- i18n: `next-intl` is wired single-locale (`en` hardcoded, `messages/en.json`, ICU plurals); no locale routing or middleware.
- Contracts: committed deterministic `contracts/openapi/v1.json` with backend export, frontend `openapi-typescript` codegen, Redocly lint, offline docs, and drift proofs.

These are verified facts about the repository, not evidence that any E6 acceptance check has run.

## Dependency reality (2026-08-14)

| Task | Dependencies | State |
| --- | --- | --- |
| E6-T4 registration/sessions | E1-T2, E3-T1 | **all done — actionable now** |
| E6-T5 contact masking/reveal | E2-T2, E3-T1, E4-T3, E6-T4 | unblocked; sequenced by plan revision 3 |
| E6-T1 test pyramid | E4-T3, E5-T3 | blocked (both proposed/draft) |
| E6-T2 privacy/security hardening | E3-T4, E4-T3, E5-T3 | blocked (all proposed/draft) |
| E6-T3 diagnostics | E3-T2, E4-T4 | blocked (both proposed) |
| E6-T6 i18n/restricted UX | E5-T3, E6-T4, E6-T5 | **done** (PR #113) |
| E6-T7 owner console | E6-T4, E6-T5 | done (PR #116) |

E3-T2–T5 remain behind implementation-plan revision 3 awaiting owner approval (PR #46); E4-T3/T4 and E5-T3–T5 remain proposed/draft. The `stacked` dependency gate cannot unlock them because their E4/E5 dependency branches do not exist.

## Options to evaluate

1. **Identity foundation: project-owned `identity` module with `pwdlib[argon2]` and opaque database sessions.**
   - E0's locked proof already omitted FastAPI Users from the architecture foundation ("adapting email-oriented defaults adds an unproven boundary").
   - The pseudonymous scope needs username/password registration, login/logout, forced-change state, and owner bootstrap — no email transport, verification, or OAuth surface that libraries center on.
   - A small feature following the existing import-linter layer contracts (pure domain + application interactors + interface transport) keeps authorization in interactors exactly as [AUTH_ADMIN_CONTACTS](../../security/AUTH_ADMIN_CONTACTS.md) requires; it also avoids a new runtime dependency to audit.
2. **FastAPI Users + SQLAlchemy wrapped by an `identity` module.**
   - [AUTH_ADMIN_CONTACTS](../../security/AUTH_ADMIN_CONTACTS.md) recommends it primarily for pwdlib hashing, cookie transport, and DB token strategy — all three are small to own directly under option 1.
   - Its escape clause explicitly returns to project-owned code if adaptation cost exceeds benefit; E0's omission and the username-only scope trigger exactly that clause.
   - Rejected for E6-T4: adapting email-oriented user-manager/transport plumbing around a fixed owner role and forced-change states adds more custom surface than it removes.
3. **Email-first hosted identity** — conflicts with accepted pseudonymous no-email scope (ADR-016). Rejected.
4. **Expose contacts in general detail responses** — defeats explicit authorization, no-store delivery, and audit minimization (ADR-011). Rejected.

## Recommendation

1. Implement E6-T4 first and alone in this planning cycle: it is the only E6 task whose dependencies are complete, it is the hard prerequisite of T5/T6/T7, and E7-T7 (production registration/reveal) waits on it. Use the project-owned identity implementation (option 1): `pwdlib[argon2]` hashing, opaque server-side sessions in HttpOnly/Secure/SameSite cookies, origin/CSRF checks on state-changing routes, per-account rate limits, forced-password-change state, and owner bootstrap via an Actions-secret-fed one-time command. New `users`/`sessions` schema in a dedicated migration; OpenAPI additions follow the committed deterministic contract flow.
2. Leave E6-T1/T2/T3/T5/T6/T7 under `proposed-tasks/` unactionable until their E3/E4/E5 dependencies complete; do not invent stacked gates for branches that do not exist. Revisit sequencing when E3 plan revision 3 is approved and E4-T3/E5-T3 promote.
3. Treat the confirmed gaps that do not require new product scope as E6-T2/T3 refinement input when those tasks promote: structlog configuration with request-scoped access logs and redaction proofs, e2e/accessibility tooling choice, and production masking of `source_text_public_masked`.

This recommendation is submitted for owner approval and does not authorize any proposed task.

## Proposed task boundaries

- [E6-T1: Complete automated test pyramid](proposed-tasks/E6-T1-complete-automated-test-pyramid.md) — boundary confirmed; blocked on E4-T3/E5-T3.
- [E6-T2: Perform privacy and security hardening](tasks/E6-T2-perform-privacy-and-security-hardening.md) — promoted under plan revision 6; dependencies E3-T4/E4-T3/E5-T3 done.
- [E6-T3: Add operational diagnostics](tasks/E6-T3-add-operational-diagnostics.md) — promoted under plan revision 7; dependencies E3-T2/E4-T4 done.
- [E6-T4: Implement in-house registration and sessions](tasks/E6-T4-implement-in-house-registration-and-sessions.md) — boundary confirmed and actionable; promoted and the first implementation-plan sequence entry.
- [E6-T5: Implement contact masking, encryption, reveal, and audit](tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md) — `done`; plan revision 3.
- [E6-T6: Implement English i18n and restricted-action UX](tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md) — `done`; plan revision 4.
- [E6-T7: Implement owner administration console](tasks/E6-T7-implement-owner-administration-console.md) — `done`; plan revision 5.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- Cookie authentication without HTTPS/CSRF/origin controls enables session abuse; T4 must ship these together or stay disabled outside production TLS.
- Rate limiting state on a single server must not silently become a second datastore; keep it in PostgreSQL or explicitly bounded in-memory with documented limits.
- Admin integration can bypass application interactors or expose hashes/tokens/contacts; T7 must reuse owner interactors only.
- Observability and fixtures can leak private source data unless redaction is verified; diagnostics (T3) must include negative redaction tests.
- The i18n base (`next-intl`, `messages/en.json`) already exists; T6 is UX/routing work, not framework adoption.
- Open question for the owner: whether E3 plan revision 3 (PR #46) should be approved first so E3-T2–T5 can unblock the rest of E6; this spike takes no position on E3 approval.
- Confirm task-level traceability, cross-epic dependencies, test evidence, rollout, and rollback during plan refinement.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.
- Owner approval of E3/E4/E5 work that completes or re-scopes a blocking dependency recorded above.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] Proposed task scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] Status is changed to `awaiting_approval` while approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of the current spike revision would permit task refinement/promotion and implementation planning only; it would not permit code.
