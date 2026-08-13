---
schema: ai-workflow/task@1
id: E7-T3
epic: E7
title: "Implement GitHub image and deployment workflows"
status: done
revision: 3
priority: P0
size: L
milestone: M3
dependencies: [E1-T4, E7-T1, E7-T2]
requirement_ids: []
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-019]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T3-implement-github-image-and-deployment-workflows.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T23:35:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T23:35:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T23:35:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (owner-authorized reconciliation)"
  verified_at: "2026-08-13T17:44:22Z"
  evidence:
    - "E1-T4 | done | merged PR https://github.com/Flippylolz/WEF/pull/8 | integrated stack f766a63"
    - "E7-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/16 | integrated stack f766a63"
    - "E7-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/17 | integrated stack f766a63"
branch:
  required: true
  name: ci/E7-T3-release-deploy
  task_id: E7-T3
  one_task_only: true
  created_at: "2026-08-12T23:39:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/18"
completion:
  completed_by: "Flippylolz (owner-authorized reconciliation)"
  completed_at: "2026-08-13T14:52:51Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/18"
  evidence:
    - "Task PR merged into the ordered stack at f766a63517b6ba49a1377e630ea54e9cb4e0e56f"
    - "Hosted release workflow published and deployed ad4d6de successfully: https://github.com/Flippylolz/WEF/actions/runs/31726996659"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E7-T3: Implement GitHub image and deployment workflows

## Outcome

Publish exact tested application images and deploy complete validated production releases from GitHub to the prepared WEF boundary under explicit event, origin, enable, trust, and concurrency gates.

## Scope

- Add a release workflow for `push` to `main` plus explicit `workflow_dispatch` SHA rehearsal.
- Run/depend on complete CI, build backend/web once, tag by full commit SHA, attach OCI revision/source labels, push to GHCR, and capture immutable digests and migration revision in a release manifest.
- Use minimum job permissions and fully pinned third-party Actions.
- Prove automatic candidates are `main` pushes associated with a merged PR targeting `main` and require repository variable `AUTO_DEPLOY_ENABLED=true`.
- Permit manual explicit-SHA rehearsal while auto deploy is disabled, but require the SHA to exist in the repository and pass the same build/tests.
- Reconstruct complete production environment from GitHub variables/secrets, validate locally without printing it, transfer via pinned-host SSH to mode-0600 temporary files, and invoke the E7-T1 locked remote deploy.
- Configure GitHub repository variables/secrets through supported APIs without exposing values; record only names/status.

## Out of scope

- Bypassing B-006, enabling auto deploy before E7-T4 rollback proof, self-hosted runners, changing branch-protection policy, storing long-lived `GITHUB_TOKEN` on the NUC, TLS/auth/contact/admin, data import, and Telegram.

## Acceptance criteria

- [x] PR/feature/hotfix/Dependabot events cannot execute production deployment.
- [x] A successful release publishes SHA-tagged backend/web images and a manifest with exact digests, source SHA, migration revision, and timestamp.
- [x] Automatic SSH requires `main`, merged-PR association, all release checks, and `AUTO_DEPLOY_ENABLED=true`; a direct main push builds but does not deploy.
- [x] Manual dispatch accepts an explicit tested SHA for rehearsal while auto deploy is false.
- [x] Deployment concurrency is serialized in GitHub and again by the host lock.
- [x] SSH host identity is pinned, config is complete/0600/atomically activated, secrets are absent from logs/artifacts/images, and transfer temporaries are removed.
- [x] Invalid/missing config fails before remote activation; workflow and negative event/origin/enable gates are testable locally.
- [x] B-006 is either resolved by a successful hosted run or remains explicitly active; local syntax cannot be presented as operational autodeploy.

## Verification evidence

- `.github/workflows/deploy-production.yml` limits automatic candidates to `push` on `main`, verifies merged-PR association and `AUTO_DEPLOY_ENABLED=true`, supports an exact-main-ancestor manual SHA, serializes production runs, and keeps deployment behind the `production` environment.
- The release job runs the locked quality/test/contract/topology/audit suite before publishing two SHA-tagged GHCR images, records immutable digests plus migration/source metadata, and transfers a checksummed non-secret artifact.
- `build_release_config.py` constructs the complete validated config from GitHub variables/secrets, rejects dotenv-unsafe passwords, writes with mode `0600`, and never prints values.
- The transfer uses a dedicated strict-known-host SSH key, bounded `/home/nuc/wef` incoming paths, remote checksum verification, atomic versioned moves, the existing host `flock`, and a transient job token that is logged out after the pull.
- The `production` GitHub environment, nine named repository variables, three environment secrets, and dedicated server public key are configured; names/status only are recorded, `AUTO_DEPLOY_ENABLED=false`, and batch login was proven without activating WEF.
- `evaluate_deploy_gate.py` and `prove_release_workflow.py` cover disabled automation, direct/unassociated pushes, merged-main candidates, manual rehearsal, pinned Actions, secret-free conditions, manifest identity, and file permissions.
- `actionlint`, Ruff, mypy, shellcheck, shell syntax checks, production topology proof, and healthy/failing deployment proofs pass locally.
- Hosted execution is proven by the successful release workflow for `ad4d6de`, including candidate verification, immutable image publication, and verified deployment.

## Test plan

- Actionlint/workflow parser plus static minimum-permission/action-pin/event/concurrency tests.
- Local execution of all build/test/contract/image commands and release-manifest validation.
- Negative gate fixture matrix for PR, direct push, wrong branch, unassociated SHA, disabled variable, invalid manual SHA, and missing secret.
- Hosted release/manual dry run when B-006 permits it; inspect GHCR digest and redacted server release record.

## Rollout and rollback

Land with `AUTO_DEPLOY_ENABLED=false`. Manual rehearsal only after E7-T2. Disable by setting the variable false; application rollback uses E7-T1/E7-T4 and never an automatic schema downgrade.

## Ready checklist

- [x] This file is authoritative under `tasks/`; its proposed source is removed.
- [x] Promotion and approved spike revision 2 are recorded.
- [x] Approved implementation-plan revision 2 and E1-T4/E7-T1/E7-T2 ancestry are recorded.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch is created and recorded.
- [x] Branch contains E7-T3 only.

## Done checklist

- [x] Acceptance criteria pass locally and in hosted release execution.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
