---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Activate the verified historical candidate publicly"
status: proposed
revision: 9
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T11
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

# Proposed Implementation Plan revision 9: Activate historical candidate publicly

> **Awaiting approval.** Follows completed E7-T7 sensitive-feature enablement on HTTPS.

## Why this revision

- E7-T6, E7-T10, and E7-T7 are `done`. ADR-019’s HTTPS and sensitive-feature gates are satisfied.
- The verified non-public candidate (`wef_hist_candidate` + checksum-scoped media) remains staged; public pointers still serve the synthetic rehearsal database/media.
- B-002/B-009 are cleared; historical public activation is the remaining M3 gate owned by E7-T11.

## Scope and outcome

Promote and execute **E7-T11 revision 1**: under `deploy.lock`, migrate/sync the candidate for identity freshness, atomically point production at the candidate database and media roots, smoke public HTTPS/API/media/privacy, and restore the previous complete configuration on any failure.

## Ordered task sequence

### 1. E7-T11 (revision 1) — Activate the verified historical candidate publicly

- Pause WEF writers; migrate candidate to the production schema head; copy production identity/session rows into the candidate when drifted.
- Atomically switch one validated release configuration: `WEF_DATABASE_URL`/`POSTGRES_DB` → `wef_hist_candidate`, media roots → `candidates/<checksum>/media/{public,originals}`.
- Public smokes on `https://2fa54e2405.duckdns.org` (health, estates/GeoJSON, derivative media, auth still works); prove `:3100` is not the public historical entry.
- On failure, restore previous DB URL + media roots + recreate services without deleting candidate or prior DB.
- Leave Forecast `:3000` and unrelated NUC workloads unchanged; no destructive cleanup (ADR-015).

## Security and operations

- No secrets/media bytes/source text in Git or logs; evidence is aggregate counts and checksums only.
- Do not bulk-flip `needs_review` offers to `visible` in this task.
- Do not remove Caddy `:3100` or Forecast `:3000`.

## Owner decision required

1. Approve **this revision 9** (or amend) under AD-009 continue authority after E7-T7.
