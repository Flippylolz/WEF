---
schema: ai-workflow/implementation-plan@1
epic: E8
title: "Future Telegram live ingestion implementation plan"
status: approved
revision: 1
owner: owner
spike_revision: 2
task_sequence:
  - id: E8-T1
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  decided_at: "2026-08-20T19:44:19Z"
  approved_revision: 1
  evidence: "AD-031; spike revision 2 approved; E8-T1 only; no Telethon/live worker enablement"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Future Telegram live ingestion

> Revision 1 authorizes **only E8-T1 revision 1** after spike revision 2.
> It does not authorize Telethon, worker Compose enablement, geocoder revalidation, or live production activation.

## Intended scope and outcome

Preserve the epic outcome: new, edited, and deleted channel posts are processed safely without changing public contracts. This revision only establishes the non-secret channel identity contract, operating-owner decision, worker-only secret paths, and a redacted verification command.

## Ordered task sequence

1. [E8-T1: Confirm channel identity and access](tasks/E8-T1-confirm-channel-identity-and-access.md) — promoted, `in_progress`.

Later revisions will promote/sequence E8-T4 → E8-T2 → E8-T3 → E8-T5 per the approved spike.

## Modules and contracts

- `wef_backend.features.ingestion.domain.telegram_channel`
- `wef_backend.features.ingestion.application.telegram_channel_verify`
- `wef_backend.features.ingestion.infrastructure.public_http`
- `wef_backend.telegram_channel_command` (`wef-verify-telegram-channel`)
- Settings: `WEF_TELEGRAM_CHANNEL_*` identity fields and `WEF_TELEGRAM_*_FILE` secret paths
- No public OpenAPI change; no schema migration

## Tests and checks

- Unit tests for identity URLs, secret mode inspection, and verification status transitions
- `make lint` / typecheck / backend tests for the touched modules

## Rollout and limits

- No production worker enablement
- No Telegram credentials in the repository
- Live Telethon resolve remains blocked until owner secrets exist and E8-T2 ships the client

## Approval checklist

- [x] Spike revision 2 is approved (AD-031).
- [x] Sequence contains only promoted E8-T1.
- [x] No proposed task appears as executable work.
- [x] Safety limit: no Telethon dependency, no worker Compose profile enablement.
