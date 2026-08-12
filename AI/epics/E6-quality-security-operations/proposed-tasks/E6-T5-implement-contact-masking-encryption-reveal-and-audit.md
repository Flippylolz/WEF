---
schema: ai-workflow/proposed-task@1
id: E6-T5
epic: E6
title: "Implement contact masking, encryption, reveal, and audit"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E2-T2, E3-T1, E4-T3, E6-T4]
requirement_ids: [P-002, P-007, P-008]
decision_ids: [ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
source: "legacy-roadmap:E6-T5"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E6-T5: Implement contact masking, encryption, reveal, and audit

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement contact masking, encryption, reveal, and audit** to the epic outcome: production behavior is tested, privacy-aware, observable, and recoverable.

## Original roadmap definition

The following definition preserves the original E6-T5 roadmap entry:

- Priority/size: P1 / L
- Dependencies: E2-T2, E3-T1, E4-T3, E6-T4
- Work:
  - Extract phone/Telegram contact spans, store encrypted values/keyed fingerprints, and generate server-side masked source text.
  - Add the authenticated no-store reveal endpoint, per-user/application and coarse edge abuse limits, and minimized `ContactReveal` audit.
- Acceptance:
  - Anonymous map/detail/source responses contain no raw extracted phone/handle.
  - Active users not awaiting forced password change can reveal only contacts for visible offers.
  - Anonymous, disabled, forced-password-change, rate-limited, and IDOR attempts fail without leakage.
  - Audit records user/offer/request/outcome/timestamp but never contact, IP/hash, or user-agent.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E2-T2](../../E2-historical-export-parser-audit/proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md), [E3-T1](../../E3-database-geocoding-media/proposed-tasks/E3-T1-create-schema-and-migrations.md), [E4-T3](../../E4-read-api-filter-contracts/proposed-tasks/E4-T3-implement-offer-detail.md), [E6-T4](E6-T4-implement-in-house-registration-and-sessions.md)
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
