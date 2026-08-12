---
schema: ai-workflow/task@1
id: E7-T1
epic: E7
title: "Build production Compose topology"
status: draft
revision: 2
priority: P0
size: L
milestone: M3
dependencies: [E1-T3, E5-T1]
requirement_ids: []
decision_ids: [ADR-005, ADR-008, ADR-010, ADR-014, ADR-015, ADR-019]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T1-build-production-compose-topology.md
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
  status: pending
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E7-T1
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E7-T1: Build production Compose topology

## Outcome

Define and locally prove an isolated, immutable-image production topology plus host-safe release scripts for the anonymous synthetic rehearsal.

## Scope

- Add `infra/compose.production.yaml` and production Caddy configuration for edge, web, API, migration, PostGIS, media, and on-demand seed/import operations.
- Publish only `${WEF_PUBLIC_PORT}:8080` from the edge; keep application/database networks and ports internal.
- Reference application images by deploy-supplied immutable digest and pin third-party images.
- Bind only `/home/nuc/wef` persistence/config paths and set restart, health, logging, read-only/tmpfs, capability, and bounded resource policies.
- Add deterministic local render/static-policy tests and host-safe preflight, deploy, smoke, and rollback scripts.
- Require explicit Compose project `wef-production`, release directory/config inputs, migration before app replacement, a deployment lock, and no global Docker cleanup.

## Out of scope

- Touching the NUC, GitHub workflow/secrets, TLS, auth/contact/admin, historical data, Telegram, backup/restore, monitoring platform, and enabling automatic deployment.

## Acceptance criteria

- [ ] Production Compose renders only with complete validated configuration and immutable web/backend image digests.
- [ ] Only configurable port 3100 is published; database/API/web ports remain internal and names cannot collide with existing projects.
- [ ] All persistent writes are under `/home/nuc/wef`; app containers use non-root/read-only boundaries and bounded logs/resources.
- [ ] Migration failure stops before app replacement; deploy commands are project/path scoped, lock-protected, and contain no prune/down-volume/destructive downgrade.
- [ ] Smoke validates public root, live/ready health, grouped GeoJSON, and release identity.
- [ ] Rollback reactivates the retained compatible application manifest without an automatic Alembic downgrade.
- [ ] Local tests prove config validation, static safety invariants, healthy replacement, and a deliberate unhealthy-release rollback using isolated temporary paths.

## Test plan

- Compose render with valid config plus negative missing/default/digest/port cases.
- Shell lint/static policy tests and an isolated fake/temporary release-state harness.
- Production image user/content checks and same-origin runtime smoke.
- Markdown links, CI syntax, secret/source exclusion, and no real server changes.

## Rollout and rollback

This task ships inert repository artifacts only. Revert the task commit to remove the topology; it does not mutate a host or database.

## Ready checklist

- [x] This file is authoritative under `tasks/`; its proposed source is removed.
- [x] Promotion and approved spike revision 2 are recorded.
- [x] Approved implementation-plan revision 2 is recorded.
- [ ] E1-T3/E5-T1 ancestry is recorded under ADR-018.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated branch is created and recorded.
- [ ] Branch contains E7-T1 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
