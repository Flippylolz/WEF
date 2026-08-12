# Definition of Done

This checklist applies to every implementation task. Epic/task acceptance criteria may add requirements but cannot weaken these gates.

## Start-state evidence

Before any code was written:

- The epic spike was explicitly owner-approved for the revision recorded by `spike_gate`.
- The task had been promoted from `proposed-tasks/` to `tasks/`.
- The epic implementation plan was explicitly owner-approved for the revision recorded by `implementation_gate`.
- Every task dependency was `done` and recorded by the satisfied dependency gate.
- The task moved through `ready` before `in_progress`.
- One dedicated branch containing the task ID was created for this task alone.

If this evidence is absent, the task cannot be declared done; restore the workflow record and obtain any required reapproval rather than retroactively assuming permission.

## Scope and acceptance

- Every task acceptance criterion and affected product requirement passes with evidence.
- The implementation matches the approved task scope and implementation plan.
- No unrelated task or opportunistic feature is included.
- Any discovered material scope, architecture, contract, security, ingestion, operations, dependency, test, migration, rollout, or rollback change followed the invalidation/reapproval rules.

## Quality

- Unit, integration, contract, end-to-end, and migration coverage is proportionate to risk.
- Applicable format, lint, type, test, migration, contract, production-build, and architecture-boundary checks pass.
- Failure, empty, loading, authorization, and accessibility states are handled where relevant.
- Backend domain/application rules are not duplicated in routes, presenters, ORM models, or frontend code.
- Public/persisted contracts are compatible or have an accepted migration/versioning plan.

## Security and data safety

- Logs, fixtures, generated artifacts, and public responses contain no credentials, secrets, Telegram sessions, raw contacts, passwords/hashes/tokens, or unreviewed personal/source data.
- Raw exports and media are absent from Git, CI artifacts, and image layers.
- Authorization, masking, rate limiting, audit minimization, and HTTPS assumptions are tested where affected.
- Uncertain parsed/geocoded values preserve provenance/confidence and are not represented as verified facts.

## Operations and documentation

- Operational changes include health checks, observability, rollback/recovery instructions, and non-interference checks as applicable.
- Deploy configuration remains owned by GitHub Actions variables/secrets and is transferred completely, safely, and atomically.
- Documentation and traceability links are updated in every affected domain.
- Accepted backup deferral and single-host data-loss risk are not misstated as backup/recovery guarantees.
- Procedural branch/PR/CI requirements are satisfied even though GitHub protection is not platform-enforced.

## Completion record

- Required reviews and CI checks pass on the dedicated task pull request.
- The pull request links the task and records test, migration, deployment, and rollback evidence.
- `completion.completed_by`, `completion.completed_at`, `completion.pull_request`, and `completion.evidence` are populated.
- The task is set to `done` only after the above evidence exists.
- The branch is squash-merged and deleted; follow-up work receives a new task and branch.
