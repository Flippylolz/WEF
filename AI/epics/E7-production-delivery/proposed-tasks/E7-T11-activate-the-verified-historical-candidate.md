---
schema: ai-workflow/proposed-task@1
id: E7-T11
epic: E7
title: "Activate the verified historical candidate publicly"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M3
dependencies: [E7-T6, E7-T7, E7-T10]
requirement_ids: [P-001, P-002, P-005, P-007]
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015, ADR-019, ADR-020]
deferred_decision_ids: []
source: "spike:E7-revision-4-activation-boundary"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T11: Activate the verified historical candidate publicly

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress. [ADR-019](../../../decisions/adr/ADR-019-anonymous-http-production-rehearsal.md) prohibits public historical-data activation until the E7-T10 HTTPS gate and the E7-T7 sensitive-feature gate pass.

## Outcome

Atomically activate the E7-T6-verified, non-public historical candidate as the public WEF release — database, media roots, and release configuration switched together — after the ADR-019 HTTPS and sensitive-feature gates pass, with public smokes and a rehearsed restoration of the previous complete configuration on any failure.

## Scope

- Briefly pause WEF writers and revalidate candidate freshness against the then-current production identity/session snapshot; rebuild the candidate from a fresh writer-paused clone if production state has drifted past the staged candidate's clone point.
- Atomically activate one complete release configuration pointing at the candidate database and candidate media roots under the WEF deployment lock; activation validates all files, upstreams, and configuration before switching current/previous pointers.
- Run public HTTPS, API, and media smokes against the activated release, including visible-pin, derivative-media, and privacy-boundary checks.
- Restore the previous complete configuration (database, media roots, release pointers) on any failed gate, without deleting candidate or prior state.
- Capture sanitized before/after inventories and completion evidence proving unrelated NUC workloads stay unchanged.

## Out of scope

- Bundle creation, transfer, candidate loading, media staging, and non-public verification: [E7-T6](../tasks/E7-T6-transfer-and-import-the-historical-dataset.md) owns them.
- E7-T10 TLS rollout itself, E7-T7 feature enablement, new parsing/geocoding/media transformations, and destructive cleanup of superseded databases/media roots/bundles (separate owner-authorized action; ADR-015 keeps same-host retention non-backup).

## Work

- Rehearse the activation and rollback sequence locally or against fixtures before touching production.
- Treat the activated configuration as one immutable unit: partial activation (new database with old media roots, or the reverse) must be impossible.
- Keep activation evidence non-sensitive: aggregate counts, health results, and checksum identities only.

## Acceptance criteria

- [ ] Activation occurs only after E7-T6 is `done`, E7-T10 has verified public HTTPS, and E7-T7 has enabled the sensitive-feature gates, satisfying ADR-019.
- [ ] Candidate freshness is revalidated (or the candidate rebuilt from a fresh writer-paused clone) immediately before activation, and production identities/sessions are preserved through cutover.
- [ ] The database, media roots, and release pointers activate as one validated atomic unit under the deployment lock, with current/previous pointers recorded.
- [ ] Public HTTPS/API/media smokes pass, every accepted visible pin and public derivative reference resolves, and restricted originals, source text, contacts, and credentials remain non-public.
- [ ] Any failed gate restores the previous complete configuration without deleting application, candidate, or certificate state, and the public release never serves a partially activated configuration.
- [ ] Before/after inventories prove unrelated NUC projects and listeners unchanged, and no historical data was publicly visible before this task's activation.
- [ ] Retained old/candidate state is described only as rollback material; cleanup requires separate owner authorization.

## Dependencies and gates

- [E7-T6](../tasks/E7-T6-transfer-and-import-the-historical-dataset.md) must be `done` with a fully verified non-public candidate.
- [E7-T10](../tasks/E7-T10-roll-out-and-verify-shared-tls.md) must be `done` so public traffic uses the verified shared Nginx HTTPS edge, not interim HTTP.
- [E7-T7](../proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) must be `done` to satisfy the ADR-019 sensitive-feature gate.
- Promotion requires a current owner-approved E7 implementation-plan revision containing E7-T11.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Security](../../../security/README.md), [Data](../../../data/README.md).

## Risks and notes

- Identity/session drift between the staged candidate clone and activation time is the main correctness risk; the freshness revalidation or rebuild requirement is mandatory, not optional.
- Activation must never expose historical data over the interim HTTP endpoint or before both ADR-019 gates pass.
- Material changes to scope, dependencies, acceptance, security, deployment, or rollback require workflow revalidation and approval.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] E7-T6, E7-T10, and E7-T7 are `done` with recorded evidence.
- [ ] The epic spike and a current implementation-plan revision explicitly authorize this activation boundary.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against them.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
