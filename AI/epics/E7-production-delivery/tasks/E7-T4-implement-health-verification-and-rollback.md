---
schema: ai-workflow/task@1
id: E7-T4
epic: E7
title: "Implement health verification and rollback"
status: in_progress
revision: 3
priority: P0
size: M
milestone: M3
dependencies: [E7-T3]
requirement_ids: []
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015, ADR-019]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T4-implement-health-verification-and-rollback.md
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
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T00:18:16Z"
  evidence:
    - "Branch ancestry contains both E7-T3 implementation and pull-request evidence commits."
branch:
  required: true
  name: ops/E7-T4-health-rollback
  task_id: E7-T4
  one_task_only: true
  created_at: "2026-08-13T00:13:45Z"
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

# E7-T4: Implement health verification and rollback

## Outcome

Prove a healthy anonymous synthetic release and compatible application rollback on the isolated NUC, then enable main-only automatic deployment only if hosted delivery works.

## Scope

- Complete production smoke for Compose health, public root/release marker, API live/ready, grouped GeoJSON/facets/offers, map style reachability, and unchanged existing services.
- Deploy a known healthy release, retain its manifest/config/images as previous, then attempt a deliberately unhealthy application release that cannot pass health.
- Verify deployment fails, restores the previous compatible application manifest, reruns smoke, and preserves PostGIS/media/Caddy state.
- Record release SHA/digests, migration revision, timestamps, failure reason, restored release, and redacted before/after inventories.
- Set `AUTO_DEPLOY_ENABLED=true` only after the hosted/manual pipeline and rollback rehearsal pass. Otherwise leave false and record the exact blocker.

## Out of scope

- Database restore, destructive migration/downgrade, backups, source import, TLS/auth/contact/admin, Telegram, and masking a hosted Actions failure with an unsafe runner.

## Acceptance criteria

- [ ] Healthy release serves the synthetic map/API through public port 3100 and reports the expected immutable release identity.
- [ ] A deliberately unhealthy release fails within a bounded timeout and restores the prior compatible application release automatically.
- [x] No automatic Alembic downgrade or database/media deletion occurs; local persistence sentinels survive healthy activation, failed replacement, rollback, and migration failure.
- [ ] Existing projects, containers, bindings, and health remain unchanged before/after healthy deploy and rollback.
- [x] Release/rollback evidence is auditable without secrets or private source data.
- [x] `AUTO_DEPLOY_ENABLED` becomes true only if hosted GHCR/deploy/rollback evidence passes; B-006 currently keeps it false.
- [ ] A later valid merged-PR main push automatically deploys only when the enable gate is true.

## Local implementation evidence

- Production smoke now has bounded network timeouts and validates the release header, web shell, exact live/ready JSON, grouped GeoJSON, facets, selected-location offers without source text, and the pinned public MapLibre style document.
- Manual dispatch offers an explicit rollback-rehearsal flag only. It requires a different prior active SHA, runs the complete candidate smoke, deliberately converts that healthy result into a health-gate failure, and treats only exit `42` plus successful previous-release smoke as rehearsal success.
- Real deployment control records mode-0600 `last-failure.json` evidence with candidate/restored SHA, reason, and timestamp. Current release/config symlinks move only after healthy smoke and return to the previous release after rollback.
- The isolated harness covers healthy activation, naturally bad release marker, reviewed forced failure, migration failure before replacement, atomic current pointers, failure evidence, and unchanged PostgreSQL/media/Caddy sentinel files.
- `verify_rollback_rehearsal.py` validates both immutable manifests, current/previous/failure state, config mode, healthy WEF services/port, and before/after non-WEF project/container/listener/HTTP equality.
- A no-network, capability-limited `db-permissions` service resolves the native `nuc:0700`/PostGIS-UID-999 bind mismatch without sudo; the exact failure/ownership/write/cleanup sequence passed on the NUC without changing the real inactive data root.
- `actionlint`, Ruff, mypy, shellcheck, release/topology proofs, expanded rollback harness, and isolated production recreate/persistence runtime pass locally. The OpenFreeMap style document was reachable and structurally valid at implementation time.
- The NUC rehearsal is intentionally not run: B-006 still prevents hosted image publication/deployment, so the first, second, fourth, and seventh criteria remain open and `AUTO_DEPLOY_ENABLED=false`.

## Test plan

- Repository/local unhealthy-image or wrong-health-marker integration harness.
- Manual hosted release to NUC followed by deliberate unhealthy release and restored smoke.
- Persistence sentinel across app replacement; no schema downgrade.
- Existing-workload inventory diff and external 3000/8080/3100 probes.
- Verify GitHub variable state and one post-enable main deployment only if B-006 is resolved.

## Rollout and rollback

The successful prior release remains retained. If rehearsal cannot restore health, stop only WEF application services, preserve database/media, leave auto deploy false, and report a blocker. Never touch other Compose projects.

## Ready checklist

- [x] This file is authoritative under `tasks/`; its proposed source is removed.
- [x] Promotion and approved spike revision 2 are recorded.
- [x] Approved implementation-plan revision 2 and E7-T3 ancestry are recorded.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch is created and recorded.
- [x] Branch contains E7-T4 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
