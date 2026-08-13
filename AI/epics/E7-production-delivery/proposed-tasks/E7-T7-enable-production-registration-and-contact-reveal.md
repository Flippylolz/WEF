---
schema: ai-workflow/proposed-task@1
id: E7-T7
epic: E7
title: "Enable production registration and contact reveal"
status: proposed
revision: 2
actionable: false
priority: P1
size: M
milestone: M3
dependencies: [E6-T4, E6-T5, E6-T6, E6-T7, E7-T4, E7-T8]
requirement_ids: [P-008]
decision_ids: [ADR-010, ADR-011, ADR-014, ADR-016, ADR-020]
deferred_decision_ids: []
source: "legacy-roadmap:E7-T7"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T7: Enable production registration and contact reveal

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Enable production registration and contact reveal** to the epic outcome: every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Original roadmap definition

The following definition preserves the original E7-T7 roadmap entry:

- Priority/size: P1 / M
- Dependencies: E6-T4, E6-T5, E6-T6, E6-T7, E7-T4
- Work:
  - Configure HTTPS, public/admin session secrets, contact encryption secrets, CSRF origin, rate limits, minimized reveal/admin audit, and one-time owner bootstrap.
  - Keep the feature disabled until production smoke/security tests pass.
- Acceptance:
  - Secure public/admin cookies, username registration/login/password change, forced owner reset, and owner console work on the public HTTPS origin.
  - Plain HTTP cannot establish/reuse a production auth/admin session or reveal contacts.
  - Reveal/admin audits contain required account/action metadata but no contact/IP/user-agent/password/token data.
  - Anonymous browsing remains available if authentication/admin is degraded.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Revision 2 refines the HTTPS dependency: E7-T8 must provide the verified shared Nginx origin before this task enables any sensitive production behavior.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E6-T4](../../E6-quality-security-operations/proposed-tasks/E6-T4-implement-in-house-registration-and-sessions.md), [E6-T5](../../E6-quality-security-operations/proposed-tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md), [E6-T6](../../E6-quality-security-operations/proposed-tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md), [E6-T7](../../E6-quality-security-operations/proposed-tasks/E6-T7-implement-owner-administration-console.md), [E7-T4](../tasks/E7-T4-implement-health-verification-and-rollback.md), and [E7-T8](E7-T8-build-shared-nginx-tls-ingress.md).
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Security](../../../security/README.md), [Data](../../../data/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P1 / M`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
