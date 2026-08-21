---
schema: ai-workflow/task@1
id: E8-T4
epic: E8
title: "Revalidate geocoder for recurring ingestion"
status: in_progress
revision: 1
priority: P2
size: M
milestone: M4
dependencies: [E3-T3]
requirement_ids: [P-001, P-007]
decision_ids: [ADR-005, ADR-006, ADR-021]
deferred_decision_ids: [D-002]
promotion:
  source: ../proposed-tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-21T07:05:27Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-21T07:05:27Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-21T07:05:27Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-21T07:05:27Z"
  evidence:
    - "E3-T3 | done | merged PR https://github.com/Flippylolz/WEF/pull/59"
branch:
  required: true
  name: feat/E8-T4-revalidate-recurring-geocoder
  task_id: E8-T4
  one_task_only: true
  created_at: "2026-08-21T07:05:27Z"
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

# E8-T4: Revalidate geocoder for recurring ingestion

## Outcome

Retain Geoapify for recurring live ingestion under dated free-plan revalidation, forbid public Nominatim for always-on jobs, and define provider-neutral quota/error defer plus redacted monitoring events for the future worker (without enabling it).

## Scope

- Recheck Geoapify free quota/terms/attribution (2026-08-21): 3000 credits/day, ≤5 rps, commercial OK with attribution; retain with WEF soft caps 2700/day and 4 rps.
- Resolve D-002: recurring provider = Geoapify; no public Nominatim recurring dependency; no automatic provider fan-out.
- Ship `wef-revalidate-recurring-geocoder` (policy report; optional `--live-check` one-credit readiness).
- Define defer dispositions: quota → next UTC day; transient/timeout/invalid → bounded defer; no-result continues through existing review path.
- Emit redacted `recurring_geocode_outcome` monitor fields for later E8-T5 alerting.
- Keep cache, precision, bounds, retry, and review semantics provider-independent (reuse E3-T3).

## Out of scope

- Telethon / live event loop (E8-T2/T3).
- Enabling the production worker Compose service (E8-T5).
- Paid Geoapify activation.
- Building a second geocoder stack.

## Acceptance criteria

- [x] No live/recurring path may select public Nominatim (`assert_provider_allowed_for_recurring`).
- [x] Cache/precision/bounds/retry/review remain on the existing provider-neutral E3-T3 path.
- [x] Dated retain decision + defer/monitor contract unit-tested; optional operator live check proves credentials/attribution via existing Geoapify readiness.
- [x] D-002 resolved for recurring Geoapify retention; B-004 cleared.

## Dependencies and gates

- Dependencies: [E3-T3](../../E3-database-geocoding-media/tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) done.
- Deferred decision: [D-002](../../../decisions/deferred/D-002-recurring-geocoding-provider.md) resolved by this task.
- Spike revision 2 and implementation plan revision 2 authorize this task.
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).

## Risks and notes

- Geoapify free commercial use still requires product attribution.
- Soft provider quotas are not relied upon; WEF hard-defers at configured budget/rate limits.
