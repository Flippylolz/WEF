---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Reversible shared-edge cutover automation"
status: awaiting_approval
revision: 5
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T9
    revision: 1
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Proposed Implementation Plan revision 5: Reversible shared-edge cutover automation

> **Not yet approved.** This document proposes the next E7 sequence after E7-T6 completion. It authorizes only E7-T9 revision 1. Owner approval of this revision and explicit restoration of [E7-T9](tasks/E7-T9-implement-reversible-shared-edge-cutover.md) from `invalidated` are both required before implementation starts.

## Why now

- [E7-T6](tasks/E7-T6-transfer-and-import-the-historical-dataset.md) is `done` (PRs #88–#104). The verified historical candidate lives in `wef_hist_candidate` on the NUC with loopback verification on `:13100`; the public release remains synthetic-only on `:3100`.
- [E7-T8](tasks/E7-T8-build-shared-nginx-tls-ingress.md) is `done` (PR #69): inert shared-edge topology, renderer, and activation helpers are proven with fixture hostnames and local Pebble ACME.
- [E7-T9](tasks/E7-T9-implement-reversible-shared-edge-cutover.md) was owner-paused on 2026-08-15 to prioritize E7-T6 while spike revision 4 was prepared. That boundary is satisfied; the task remains `invalidated` until the owner restores it.

## Approved spike baseline

- [Spike revision 4](SPIKE.md) remains current and preserves the revision-3 shared-edge design.
- Binding constraints unchanged: no live NUC mutation, no real DNS/ACME, no public 80/443 checks, no router/firewall changes, and no removal of application-port forwarding in this task.
- [D-009](../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md) still gates only [E7-T10](proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md).

## Scope and outcome

Deliver locally proven, host-safe automation that can move WEF and AI Forecast behind the isolated shared edge in independently verified stages and restore the previous validated configuration/listeners on failure. Repository changes only; server execution belongs to E7-T10 after D-009 resolution.

## Ordered task sequence

### 1. E7-T9 — Implement reversible shared-edge cutover

- Task: [E7-T9 revision 1](tasks/E7-T9-implement-reversible-shared-edge-cutover.md).
- Independently reviewable: cutover-safe WEF release variant, shared-edge preflight/inventory/render/activate/smoke/rollback commands under `scripts/deploy/`, and fixture-based integration evidence.
- Dependencies: E7-T8 `done`; E7-T6 completion removes the owner pause rationale but does not auto-restore the task.
- Affected modules/contracts: production Compose/release artifacts gain an explicit shared-edge cutover variant; existing Caddy `:3100` rehearsal remains complete rollback material; AI Forecast continues through its retained host-port upstream without Compose-project ownership changes.
- Tests: unit/static schema and forbidden-command patterns; fixture upstream routing, redirect gate, atomic pointers, failure injection, and previous-release restoration.
- Rollout: inert automation and fixture evidence only; revert the dedicated PR to roll back repository changes.

## Cross-task architecture

- WEF cleanup must not remove the external edge network; edge cleanup must not run WEF or AI Forecast Compose commands.
- Use explicit Linux host-gateway mapping for the unchanged AI Forecast host listener; do not depend on undocumented bridge addresses.
- Never switch current pointers or redirects until config validation and both upstream health checks pass.
- Rollback restores the exact previous edge release and listener/forwarding intent; it never deletes certificates, application state, or databases.

## Security and operations

- No sensitive WEF feature activation, data import, backups, or data/schema rollback.
- No production/server/network mutation occurs in this task.
- Public application/API contracts and persisted database/media data remain unchanged.

## Risks and mitigations

- **Cross-project interference:** strict project/network allowlists, inventory diff gates, and forbidden Compose command patterns in tests.
- **Premature redirect activation:** HTTP redirects activate only after both HTTPS fixture routes pass independent smokes.
- **AI Forecast ownership drift:** routing uses only the retained host listener; no command targets its Compose project/resources.

## Invalidation triggers

Return to the spike for cross-project database/shared-edge ownership changes, live DNS/ACME, or public listener mutation. Return to this plan for material changes to cutover stages, rollback boundaries, or task order.

## Owner decision required

1. Approve **E7 IMPLEMENTATION_PLAN revision 5** (this document).
2. Restore **E7-T9** from `invalidated` to `ready` (or equivalent) with updated spike/implementation gate records.
3. Optionally resolve **D-009** hostnames/forwarding before scheduling **E7-T10** live rollout.

After both (1) and (2), E7-T9 may start on a dedicated branch per the [workflow](../../workflow/README.md).
