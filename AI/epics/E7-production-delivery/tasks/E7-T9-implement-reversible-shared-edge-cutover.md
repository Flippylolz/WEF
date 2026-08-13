---
schema: ai-workflow/task@1
id: E7-T9
epic: E7
title: "Implement reversible shared-edge cutover"
status: draft
revision: 1
priority: P1
size: L
milestone: M3
dependencies: [E7-T8]
requirement_ids: []
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-019, ADR-020]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T9-implement-reversible-shared-edge-cutover.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T19:32:59Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:32:59Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:32:59Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E7-T9
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

# E7-T9: Implement reversible shared-edge cutover

## Outcome

Provide locally proven, host-safe automation that can move WEF and AI Forecast behind the isolated shared edge in independently verified stages and restore the previous validated configuration/listeners on failure.

## Scope

- Add a cutover-safe WEF release variant that exposes web/API/media only to the explicitly managed edge network while preserving the current Caddy release as rollback material.
- Route AI Forecast through its retained host-port upstream without joining, editing, recreating, or owning its Compose project.
- Generate complete edge releases from validated non-secret variables and secret files, then activate immutable current/previous pointers atomically.
- Capture redacted before/after project, container, image, network, volume, listener, resource, and application-health inventories.
- Validate port/path/network ownership, Nginx configuration, certificate presence, upstream health, and route-specific smokes before each stage.
- Stage HTTP redirects only after both HTTPS routes pass; add bounded failure injection and automatic previous-config/listener restoration.

## Out of scope

- Live NUC mutation, real DNS/ACME, public 80/443 checks, router/firewall changes, and removal of public application-port forwarding.
- AI Forecast image, application, database, API, Compose project, persistent resource, or behavior changes.
- Sensitive WEF feature activation, data import, backups, or data/schema rollback.

## Affected modules and contracts

- Production Compose/release artifacts gain an explicit shared-edge cutover variant without changing the current default rehearsal manifest.
- `scripts/deploy/` gains shared-edge preflight, inventory, render, activate, smoke, and rollback commands.
- Existing release-state helpers remain authoritative for atomic current/previous state and are extended only where edge-specific state requires it.
- Public application/API contracts and persisted database/media data remain unchanged.

## Implementation notes

- Keep current Caddy/3100 and AI Forecast/3000 listeners until the future live task proves replacement; local tests use fixtures only.
- Use an explicit Linux host-gateway mapping for the unchanged AI Forecast host listener. Do not depend on undocumented bridge addresses.
- WEF cleanup must not remove the external edge network; edge cleanup must not run WEF or AI Forecast Compose commands.
- Never switch current pointers or redirects until config validation and both upstream health checks pass.
- Rollback restores the exact previous edge release and listener/forwarding intent; it never deletes certificates, application state, or databases.

## Acceptance criteria

- [ ] WEF has a validated private-upstream cutover variant while the existing Caddy rehearsal remains a complete rollback path.
- [ ] AI Forecast routing uses only its retained host listener and no command targets its Compose project/resources.
- [ ] Complete edge release config is validated, transferred with restrictive modes, and atomically activated through auditable current/previous state.
- [ ] Preflight aborts before mutation on occupied ports, missing paths/networks/certificates, invalid Nginx config, unhealthy upstreams, or unexpected inventory changes.
- [ ] Independent WEF web/API/media/release-marker and AI Forecast frontend/API smokes pass through fixture host routes.
- [ ] HTTP redirects activate only after both HTTPS routes are healthy.
- [ ] Deliberate invalid config and unavailable WEF/AI upstream failures restore the previous validated edge release and leave both application states unchanged.
- [ ] Before/after evidence proves DuckDNS, WireGuard, PostgreSQL, WEF persistence, AI Forecast resources, and unrelated Docker resources are unchanged.
- [ ] No production/server/network mutation occurs.

## Test plan

- Unit/static: complete config schema, path/port/project/network allowlists, redaction, rollback state, and forbidden command patterns.
- Integration: WEF/AI fixture upstreams, host-header routing, health/smoke stages, redirect gate, atomic pointers, config activation, and previous release restoration.
- Failure injection: occupied listener, malformed config, missing certificate, each unavailable upstream, failed reload, stale inventory, and interrupted activation.
- Repository: format, lint, type, tests, contracts, Markdown links, action/shell validation, production proof, and runtime images.

## Rollout and rollback

This task creates inert automation and fixture evidence only. Revert its dedicated PR to roll back repository changes. E7-T10 alone may execute the automation on the server after D-009 and a current plan revision are approved.

## Ready checklist

- [x] This file is authoritative under `tasks/`; no proposed duplicate exists.
- [x] Promotion and current spike/implementation gates are recorded.
- [ ] E7-T8 has an open ancestor PR recorded by a stacked dependency gate or is done.
- [x] D-009 is absent because live rollout belongs to E7-T10.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated E7-T9 branch is created and recorded.
- [ ] Branch contains E7-T9 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
