---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Operational diagnostics for production operators"
status: approved
revision: 7
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T3
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T16:34:05Z"
  approved_revision: 7
  evidence: "Owner continue after E6-T2; AD-009 bounded plan revision; E6 spike revision 2; E6-T3 dependencies E3-T2/E4-T4 done"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Operational diagnostics (revision 7)

> Revision 7 authorizes only E6-T3 revision 1 after E6-T2.

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved.
- Binding docs: [DEPLOYMENT](../../operations/DEPLOYMENT.md), ADR-008/010/014/015.
- E6-T2 is `done`; E3-T2 and E4-T4 are `done`.

## Scope and outcome

Give operators a non-sensitive way to identify the active release, last deploy failure stage/reason, disk pressure on WEF roots, and last successful import aggregates, plus structured request access logs with redaction proofs.

## Ordered task sequence

### 1. E6-T3 (revision 1) — Add operational diagnostics

- Task: [E6-T3](tasks/E6-T3-add-operational-diagnostics.md).
- Independently reviewable: deploy diagnostics script + logging middleware/config + tests/docs.
- Dependencies: E3-T2, E4-T4 — both `done`.
- Affected modules: `scripts/deploy/operator_diagnostics.py`, backend logging/middleware, operations docs, CI unittest list.
- Tests: fixture-based diagnostics JSON; redaction negative tests (no password/token/source text); access-log fields present.
- Out of scope: E6-T1, full metrics backends, backups, Telegram.

## Security and privacy

- Diagnostics emit checksums, counts, stages, and paths only — never source text, contacts, cookies, or DB URLs with credentials.
- Access logs include method/path/status/duration/request_id/release_sha only.

## Operations, rollout, and rollback

- Script runs on the NUC against `$WEF_ROOT`; optional `docker exec` for import-run query.
- Logging activates on next API deploy; rollback is prior image/script.

## Owner decision

Flippylolz authorized continuation after E6-T2 (chat continue 2026-08-20). Revision 7 sequences E6-T3 revision 1 only.
