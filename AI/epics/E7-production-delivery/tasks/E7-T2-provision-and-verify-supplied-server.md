---
schema: ai-workflow/task@1
id: E7-T2
epic: E7
title: "Provision and verify supplied server"
status: done
revision: 2
priority: P0
size: M
milestone: M3
dependencies: [E7-T1]
requirement_ids: []
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015, ADR-019]
deferred_decision_ids: [D-001]
promotion:
  source: ../proposed-tasks/E7-T2-provision-and-verify-supplied-server.md
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
    - "E7-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/16 | integrated stack f766a63"
branch:
  required: true
  name: chore/E7-T2-provision-server
  task_id: E7-T2
  one_task_only: true
  created_at: "2026-08-13T00:00:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/17"
completion:
  completed_by: "Flippylolz (owner-authorized reconciliation)"
  completed_at: "2026-08-13T14:52:50Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/17"
  evidence:
    - "Task PR merged into the ordered stack at f766a63517b6ba49a1377e630ea54e9cb4e0e56f"
    - "Integrated main CI passed for ad4d6de: https://github.com/Flippylolz/WEF/actions/runs/31726996540"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E7-T2: Provision and verify supplied server

## Outcome

Prepare the WEF-only NUC boundary and prove its capacity, port, routing, permissions, and non-interference without changing existing workloads.

## Scope

- Verify pinned SSH host identity, Docker/Compose versions, `/home/nuc` capacity, memory, port 3100, and required outbound GHCR/map connectivity.
- Capture redacted before/after inventories of Compose projects, running containers/images/status, published listeners, WEF path, and existing 3000/8080/51820 health.
- Create only `/home/nuc/wef` release, secret, PostgreSQL, media, import, Caddy, state, and log directories with least-access permissions.
- Install/transfer only E7-T1 versioned inert manifests/scripts into the WEF release boundary and validate production Compose without starting it.
- Record conservative CPU/memory/log ceilings for the shared 8 GB host.
- Start a synthetic/empty rehearsal only when immutable images are available; otherwise stop at a clean prepared boundary and record B-006.

## Out of scope

- Sudo/firewall/router mutation, existing-project changes, global Docker cleanup, source archive transfer, historical import, TLS, auth/contact/admin, Telegram, and GitHub repository configuration.

## Acceptance criteria

- [x] Strict SSH host verification and non-interactive `nuc` Docker access pass without storing/administering a sudo password.
- [x] Preflight aborts if port 3100 is occupied, capacity is insufficient, config is invalid, or a non-WEF path/project would be targeted.
- [x] `/home/nuc/wef` is the only created/modified host tree and restrictive directory/file modes are recorded.
- [x] Before/after evidence proves AI Forecast, DuckDNS, WireGuard, ports 3000/8080/51820, and their health remain unchanged.
- [x] The external port-3100 check is attempted only while the WEF edge is intentionally listening; no edge/image exists yet, so E7-T4 retains the router reachability check.
- [x] No source export, credential, session, media payload, or default secret is transferred.

## Test plan

- Read-only host inventory before and after each bounded mutation.
- Remote production Compose render and preflight negative cases.
- Existing-service HTTP/listener/container identity comparison.
- External anonymous root/health/map smoke only if a release starts.

## Rollout and rollback

Stop only the `wef-production` project if started. Preserve PostgreSQL/media by default. Remove only E7-T2-created empty/temp WEF artifacts when safe; never remove `/home/nuc/wef` wholesale without explicit owner authorization.

## Ready checklist

- [x] This file is authoritative under `tasks/`; its proposed source is removed.
- [x] Promotion and approved spike revision 2 are recorded.
- [x] D-001 is resolved for the anonymous rehearsal by ADR-019.
- [x] Approved implementation-plan revision 2 and E7-T1 ancestry are recorded.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch is created and recorded.
- [x] Branch contains E7-T2 only.

## Done checklist

- [x] Acceptance criteria pass for the bounded preparation task.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.

## Verification evidence

- Review: [stacked PR #17](https://github.com/Flippylolz/WEF/pull/17), based on E7-T1 PR #16.
- Access: strict known-host checking, batch SSH key authentication, `nuc` identity, Docker/Compose, Python, curl, flock, `ss`, awk, and disk tools passed without sudo.
- Before/after: the automated inventory comparator found the exact same three Compose projects, five container IDs/image IDs/states/health/port bindings, watched listeners, and existing HTTP status codes after provisioning.
- Capacity: post-provision evidence recorded approximately 941 GB free and 6.35 GiB available memory; port 3100 remained unbound.
- Paths: only `/home/nuc/wef` was introduced. General/persistence directories are owner `nuc` mode 0750, while secrets/PostgreSQL directories are mode 0700.
- Release: inert E7-T1 commit `394329cb6a1a00f97c9a8533336667d1c072d2ac` manifests/scripts were transferred mode 0640/0750, validated with a temporary non-default fixture, and left with no active config/current-release state.
- Exclusions: no source archive, media payload, GitHub/Telegram credential, session, real production env, container, network, listener, or database was created.
- Subsequent hosted release evidence resolved B-006 and exercised the prepared WEF boundary; E7-T4 records the completed release verification.
