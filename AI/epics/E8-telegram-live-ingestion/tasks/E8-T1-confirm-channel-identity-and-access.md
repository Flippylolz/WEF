---
schema: ai-workflow/task@1
id: E8-T1
epic: E8
title: "Confirm channel identity and access"
status: in_progress
revision: 1
priority: P2
size: S
milestone: M4
dependencies: []
requirement_ids: [P-006]
decision_ids: [ADR-006]
deferred_decision_ids: [D-003]
promotion:
  source: ../proposed-tasks/E8-T1-confirm-channel-identity-and-access.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T19:44:19Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T19:44:19Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T19:44:19Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T19:44:19Z"
  evidence:
    - "M3 | done | public MVP exit evidence"
branch:
  required: true
  name: feat/E8-T1-channel-identity-access
  task_id: E8-T1
  one_task_only: true
  created_at: "2026-08-20T19:44:19Z"
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

# E8-T1: Confirm channel identity and access

## Outcome

Non-secret expected channel identity, operating-owner decision, worker-only secret path contract, and a redacted verification command are recorded. Live Telethon entity resolve remains gated on owner-supplied secrets and E8-T2.

## Scope

- Record expected username `elestate_warszawa`, numeric channel ID `2180077318`, title, and `https://t.me/elestate_warszawa/{message_id}` link template (aligned with historical import settings and D-003).
- Decide operating owner: one dedicated least-privilege Telegram **user** account (not a bot).
- Define worker-only secret files: API ID, API hash, Telethon string session at mode `0600` paths (defaults under `/run/secrets/`).
- Ship `wef-verify-telegram-channel`: public message reachability + redacted secret-path inspection; no Telethon dependency; never prints secret contents.
- Update D-003 for the public identity contract; keep live API authorization open until secrets exist.

## Out of scope

- Telethon client, session bootstrap UI, backfill, live event loop (E8-T2/T3).
- Enabling the production worker Compose service (E8-T5).
- Storing credentials in Git, images, env dumps, or the database.

## Acceptance criteria

- [x] Non-secret expected channel identity is configured and unit-tested.
- [x] Public message link probe succeeds in verification (mocked in CI; live URL checked by operator CLI).
- [x] Secret path contract is inspected without reading/echoing secret bytes; missing secrets yield an explicit non-success status.
- [x] Live Telethon resolve of numeric ID/title against expected values (verified by the
  authorized E15 recovery against channel `2180077318`).
- [x] Credentials/session present only in the approved secret path on the NUC
  (redacted worker readiness and deploy-managed path verification; values not read).

Operational acceptance evidence is recorded in
[E15 production recovery evidence](../../E15-telegram-ingestion-reliability/PRODUCTION_EVIDENCE.md).
Task completion metadata remains separate from E15-T3.

## Dependencies and gates

- Dependencies: none (M3 prerequisite satisfied).
- Deferred decision: [D-003](../../../decisions/deferred/D-003-telegram-channel-access.md) partially resolved for public identity; live access remains open.
- Spike revision 2 and implementation plan revision 1 authorize this task.
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).

## Risks and notes

- Missing GitHub/NUC Telegram secrets keep live acceptance open (B-003).
- Public `t.me` reachability is necessary but not sufficient proof of API edit/delete delivery.
