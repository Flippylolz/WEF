---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Activate the verified historical candidate publicly"
status: approved
revision: 9
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T11
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T15:40:00Z"
  approved_revision: 9
  evidence: "Owner continue after E7-T7; AD-009 bounded plan revision; ADR-019 HTTPS and sensitive-feature gates satisfied"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Activate historical candidate publicly (revision 9)

> Revision 9 authorizes only E7-T11 revision 1 after completed E7-T6, E7-T10, and E7-T7.

## Approved spike baseline

- [Spike revision 4](SPIKE.md) remains current.
- [ADR-019](../../decisions/adr/ADR-019-anonymous-http-production-rehearsal.md) requires E7-T10 HTTPS and E7-T7 before public historical data; both are `done`.
- E7-T6 staged `wef_hist_candidate` and checksum-scoped media without changing public pointers.

## Scope and outcome

Atomically activate the verified historical candidate as the public WEF release (database + media roots + release configuration) under the deployment lock, with identity freshness, public HTTPS smokes, and rehearsed rollback of the previous complete configuration.

## Ordered task sequence

### 1. E7-T11 (revision 1) — Activate the verified historical candidate publicly

- Task: [E7-T11](tasks/E7-T11-activate-the-verified-historical-candidate.md).
- Under `deploy.lock`, migrate the candidate to the production schema head and sync production `users`/`auth_sessions` when drifted.
- Switch production `WEF_DATABASE_URL` to `wef_hist_candidate` and point host media roots at `candidates/<bundle_checksum>/media/{public,originals}` as one validated unit.
- Smoke HTTPS health/API/media/privacy and owner session continuity; keep Forecast `:3000` and Caddy `:3100` unchanged as non-public/rollback surfaces.
- On any failed gate, restore the previous DB URL and media roots without deleting candidate or prior state.

## Security and operations

- Aggregate evidence only; no bulk visibility promotion of `needs_review` offers.
- Retained old DB/media/candidate are rollback material (ADR-015); cleanup needs separate owner authorization.

## Invalidation triggers

Return to the spike if activation becomes a destructive overwrite of production identity, a non-atomic DB/media split, or public historical exposure over interim HTTP.

## Owner decision

Flippylolz authorized continuation after E7-T7 (chat continue 2026-08-20). Revision 9 sequences E7-T11 revision 1 only.
