---
schema: ai-workflow/epic@1
id: E28
title: Reliable delivery of every new channel offer to the map
status: in_progress
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E28: Every new offer reaches the map with its gallery

The channel contains offer albums. Successful transport alone is insufficient: each offer-bearing post must converge to one traceable map-visible offer with the correct source-supported position and its images. Media-only album posts attach to that offer. Edits/reposts must not duplicate offers or cross-attach galleries.

The [completed spike](SPIKE.md) identifies four hidden offers among the five most recent offer-bearing posts. The [implementation plan](IMPLEMENTATION_PLAN.md) sequences five independent fixes and acceptance work. [Owner direction](OWNER_DIRECTION.md) explicitly authorizes research followed by implementation.

## Tasks

- [E28-T1: Recognize current offer templates](tasks/E28-T1-current-offer-templates.md).
- [E28-T2: Resolve valid Warsaw street locations](tasks/E28-T2-warsaw-street-resolution.md).
- [E28-T3: Support source-evidenced nearby localities](tasks/E28-T3-nearby-localities.md).
- [E28-T4: Reconnect galleries after offer recovery](tasks/E28-T4-recovered-offer-galleries.md).
- [E28-T5: Verify and monitor complete offer delivery](tasks/E28-T5-map-delivery-acceptance.md).

## Acceptance

All five audited offer-bearing posts must reach the public map with their correct gallery after bounded recovery. The Dosin house must retain its actual locality and honest approximate precision. Neither a green worker status nor parser `complete` is delivery acceptance. Measure unique current offer revisions, map-visible offers, current associated photos, oldest unresolved age, and reasons; do not confuse descriptor attempts or old revisions with unique missing photos. New offers should publish within five minutes when provider availability/budget allows; delays remain retryable and observable. Completion additionally requires a 24-hour live window and deterministic edit/replay/restart tests, without silently exempting unclassified posts.

## Rollout

The initial T1–T4 releases passed production canaries; district/street follow-ups
remain under acceptance. T5 code is merged and its parser backfill completed;
[production acceptance](PRODUCTION_ACCEPTANCE.md) tracks the bounded backfill and
real 24-hour delivery window. E28 remains in progress until that window passes.
