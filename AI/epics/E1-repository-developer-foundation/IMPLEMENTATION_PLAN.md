---
schema: ai-workflow/implementation-plan@1
epic: E1
title: "Dependabot update pull requests"
status: approved
revision: 5
owner: owner
spike_revision: 2
task_sequence:
  - id: E1-T6
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T17:53:13Z"
  approved_revision: 5
  evidence: "Owner continue after E6/favorites; AD-009 bounded plan revision; E1 spike revision 2; E1-T1/E1-T4 done; E1-T7 remains proposed"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Dependabot updates (revision 5)

> Revision 5 authorizes only E1-T6 revision 1 after the E1 repository-foundation sequence (revision 4) completed.

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved.
- Binding docs: [REPOSITORY_RULES Dependabot](../../governance/REPOSITORY_RULES.md), ADR-017.
- E1-T1 and E1-T4 are `done`; E1-T5 remains cancelled; E1-T7 stays proposed.

## Scope and outcome

Configure Dependabot so GitHub opens weekly version-update and security-update pull requests for every committed dependency ecosystem (npm workspace, Python/backend, Dockerfiles, GitHub Actions), with compatible patch/minor grouping and a bounded open-PR limit. Major upgrades remain separate/manual. Auto-merge remains out of scope (E1-T7).

## Ordered task sequence

### 1. E1-T6 (revision 1) — Configure Dependabot update pull requests

- Task: [E1-T6](tasks/E1-T6-configure-dependabot-update-pull-requests.md).
- Independently reviewable: committed `.github/dependabot.yml` plus documentation/index updates that match REPOSITORY_RULES.
- Dependencies: E1-T1, E1-T4 — both `done`.
- Affected modules: `.github/dependabot.yml`, E1 indexes/SPIKE notes, autonomous decision log.
- Verification: YAML structure covers npm/pip/docker/github-actions; patch/minor groups present; majors ungrouped; no merge-controller workflow.
- Out of scope: E1-T7 merge controller, branch protection, upgrading dependencies in this change.

## Safety and privacy

- No secrets, production credentials, or PR checkout/execution.
- Dependabot PRs use the existing unprivileged CI pipeline only.

## Invalidation triggers

- Material change to Dependabot ecosystems, grouping policy, or merge automation scope.
- Evidence that npm workspace / uv.lock / Dockerfile directories cannot be covered by the configured directories.

## Approval checklist

- [x] Spike revision 2 remains current for Dependabot boundaries.
- [x] E1-T6 dependencies are `done`.
- [x] E1-T7 remains explicitly excluded.
- [x] AD-009 continue authority recorded as AD-029.
