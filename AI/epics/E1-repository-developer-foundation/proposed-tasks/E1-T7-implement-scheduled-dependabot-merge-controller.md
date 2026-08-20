---
schema: ai-workflow/proposed-task@1
id: E1-T7
epic: E1
title: "Implement scheduled Dependabot merge controller"
status: proposed
revision: 1
actionable: false
priority: P0
size: M
milestone: M1
dependencies: [E1-T4, E1-T6]
requirement_ids: []
decision_ids: [ADR-017]
deferred_decision_ids: []
source: "legacy-roadmap:E1-T7"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E1-T7: Implement scheduled Dependabot merge controller

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement scheduled Dependabot merge controller** to the epic outcome: a reproducible monorepo that cannot accidentally commit or package the source archive/media.

## Original roadmap definition

The following definition preserves the original E1-T7 roadmap entry:

- Priority/size: P0 / M
- Dependencies: E1-T4, E1-T6
- Work:
  - Add the 15-minute/manual scheduled controller specified in [repository and change rules](../../../governance/REPOSITORY_RULES.md).
  - Require owner-applied `automerge`, Dependabot-only authorship, current base, explicit successful-check allowlist, mergeability, and patch/minor metadata.
  - Refetch state and squash merge with `--match-head-commit` so the verified PR head cannot change; never check out/execute PR code with the write token.
- Acceptance:
  - An owner-labeled, bot-only patch/minor PR with the exact expected successful checks is squash-merged and its branch deleted.
  - Missing/failed/pending checks, stale base, conflicts, missing/wrong label actor, human commits, changed head SHA, indirect/major updates, or wrong author/base/head prevent merge with a recorded reason.
  - Tests cover every allow/deny condition and the head-change race.
  - The workflow uses pinned Actions, minimum permissions, one concurrency group, and no PR checkout.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T4](../tasks/E1-T4-establish-ci-baseline.md), [E1-T6](../tasks/E1-T6-configure-dependabot-update-pull-requests.md)
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Decision registry](../../../decisions/README.md), [Architecture](../../../architecture/README.md), [Governance](../../../governance/README.md), [Operations](../../../operations/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P0 / M`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
