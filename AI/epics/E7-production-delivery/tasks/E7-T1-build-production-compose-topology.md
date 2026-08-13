---
schema: ai-workflow/task@1
id: E7-T1
epic: E7
title: "Build production Compose topology"
status: done
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
  status: satisfied
  verified_by: "Cursor Agent (owner-authorized reconciliation)"
  verified_at: "2026-08-13T17:44:22Z"
  evidence:
    - "E5-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/14 | integrated stack f766a63"
    - "E1-T3 | done | merged PR https://github.com/Flippylolz/WEF/pull/9 | integrated stack f766a63"
branch:
  required: true
  name: feature/E7-T1-production-compose
  task_id: E7-T1
  one_task_only: true
  created_at: "2026-08-12T23:38:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/16"
completion:
  completed_by: "Flippylolz (owner-authorized reconciliation)"
  completed_at: "2026-08-13T14:52:49Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/16"
  evidence:
    - "Task PR merged into the ordered stack at f766a63517b6ba49a1377e630ea54e9cb4e0e56f"
    - "Integrated main CI passed for ad4d6de: https://github.com/Flippylolz/WEF/actions/runs/31726996540"
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

- [x] Production Compose renders only with complete validated configuration and immutable web/backend image digests.
- [x] Only configurable port 3100 is published; database/API/web ports remain internal and names cannot collide with existing projects.
- [x] All persistent writes are under `/home/nuc/wef`; app containers use non-root/read-only boundaries and bounded logs/resources.
- [x] Migration failure stops before app replacement; deploy commands are project/path scoped, lock-protected, and contain no prune/down-volume/destructive downgrade.
- [x] Smoke validates public root, live/ready health, grouped GeoJSON/facets/offers, and release identity.
- [x] Rollback reactivates the retained compatible application manifest without an automatic Alembic downgrade.
- [x] Local tests prove config validation, static safety invariants, healthy replacement, and a deliberate unhealthy-release rollback using isolated temporary paths.

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
- [x] E1-T3/E5-T1 ancestry is recorded under ADR-018.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch is created and recorded.
- [x] Branch contains E7-T1 only.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.

## Verification evidence

- Static topology: `make production-proof` renders all profiles to JSON, requires GHCR digests/complete non-placeholder config, proves one edge publication/internal application networking, validates resource/read-only/capability/logging/path rules, and validates the pinned Caddy configuration.
- Script safety: Ruff/mypy/ShellCheck/`sh -n` pass; static policy rejects global Docker prune, `down -v`, destructive Alembic downgrade, and references to existing NUC project paths.
- Failure control flow: an isolated fake-command harness activates a healthy release, rejects/restores a deliberately unhealthy candidate, preserves the previous state, and proves a migration failure stops before application replacement.
- Real runtime: `make production-runtime-proof` uses a unique temporary Compose project/path and local non-root images, migrates/seeds the explicit production rehearsal, serves the root/health/map/facets/offers contract through Caddy, tears every container/network down, recreates the stack without reseeding, and proves bind-mounted catalog persistence.
- Non-interference: the existing `wef-local` API/web/PostGIS/Caddy remained healthy on loopback 3100; the temporary production-proof project left no containers or files.
- Seed boundary: production remains denied by default; only the profile-gated seed service plus `WEF_ALLOW_SYNTHETIC_SEED=true` can insert the clearly synthetic fixture.
- Review: [stacked PR #16](https://github.com/Flippylolz/WEF/pull/16) merged after its base sequence; hosted integrated CI is now green.
