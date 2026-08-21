---
schema: ai-workflow/implementation-plan@1
epic: E8
title: "Future Telegram live ingestion implementation plan"
status: approved
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E8-T1
    revision: 1
  - id: E8-T4
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  decided_at: "2026-08-21T07:05:27Z"
  approved_revision: 2
  evidence: "AD-032; spike revision 2 approved; E8-T1 then E8-T4; no Telethon/live worker enablement"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Future Telegram live ingestion

> Revision 2 authorizes **E8-T1 revision 1** and **E8-T4 revision 1** after spike revision 2.
> It does not authorize Telethon, worker Compose enablement, or live production activation.

## Intended scope and outcome

Preserve the epic outcome: new, edited, and deleted channel posts are processed safely without changing public contracts. Revision 1 established the non-secret channel identity contract. Revision 2 revalidates Geoapify for recurring use, resolves D-002, and defines quota/error defer plus monitoring hooks for the future worker.

## Ordered task sequence

1. [E8-T1: Confirm channel identity and access](tasks/E8-T1-confirm-channel-identity-and-access.md) — promoted, `in_progress` (secrets/live resolve still open).
2. [E8-T4: Revalidate geocoder for recurring ingestion](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — promoted under this revision.

Later revisions will promote/sequence E8-T2 → E8-T3 → E8-T5 per the approved spike.

## Modules and contracts

- `wef_backend.features.ingestion.domain.recurring_geocoder`
- `wef_backend.features.ingestion.application.recurring_geocode`
- `wef_backend.recurring_geocoder_command` (`wef-revalidate-recurring-geocoder`)
- Reuses E3-T3 `ResolveGeocode` / durable budget / review without Nominatim recurring wiring
- No public OpenAPI change; no schema migration

## Tests and checks

- Unit tests for retain decision, Nominatim forbid, defer classification, redacted monitor events
- `make lint` / typecheck / backend tests for the touched modules

## Rollout and limits

- No production worker enablement
- No Telethon dependency
- No paid Geoapify activation
- Operator may run `wef-revalidate-recurring-geocoder [--live-check]`

## Approval checklist

- [x] Spike revision 2 is approved (AD-031).
- [x] Sequence contains only promoted E8-T1 and E8-T4.
- [x] No proposed task appears as executable work.
- [x] Safety limit: no Telethon dependency, no worker Compose profile enablement.
