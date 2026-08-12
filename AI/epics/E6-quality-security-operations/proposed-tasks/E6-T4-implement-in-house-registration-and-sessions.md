---
schema: ai-workflow/proposed-task@1
id: E6-T4
epic: E6
title: "Implement in-house registration and sessions"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E1-T2, E3-T1]
requirement_ids: [P-008]
decision_ids: [ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
source: "legacy-roadmap:E6-T4"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E6-T4: Implement in-house registration and sessions

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement in-house registration and sessions** to the epic outcome: production behavior is tested, privacy-aware, observable, and recoverable.

## Original roadmap definition

The following definition preserves the original E6-T4 roadmap entry:

- Priority/size: P1 / L
- Dependencies: E1-T2, E3-T1
- Work:
  - Implement [authentication, administration, and contact reveal](../../../security/AUTH_ADMIN_CONTACTS.md): username/password registration, login/logout, password change, account/session management, Argon2, opaque database-backed HttpOnly sessions, and forced-password-change state.
  - Use FastAPI Users only if E0-T2 proves its username-only adaptation is smaller/safer than focused project-owned identity code.
  - Add CSRF/origin checks, generic anti-enumeration responses, session revocation, and auth rate limits.
- Acceptance:
  - Anonymous browsing remains unaffected.
  - Registration/login/logout/password-change/revocation/account-disable/delete flows pass integration/security tests.
  - Raw tokens, passwords, hashes, and session cookies do not appear in logs/public responses.
  - No email, verification, or self-service forgotten-password dependency exists.
  - Public contact reveal remains disabled over non-HTTPS production configuration.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T2](../../E1-repository-developer-foundation/tasks/E1-T2-scaffold-web-and-backend-applications.md), [E3-T1](../../E3-database-geocoding-media/tasks/E3-T1-create-schema-and-migrations.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Product](../../../product/README.md), [Security](../../../security/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Contracts](../../../contracts/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P1 / L`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
