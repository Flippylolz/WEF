---
schema: ai-workflow/epic@1
id: E21
title: "Ingestion AI fallback on parse miss"
status: done
milestones: [M5]
owner: owner
---

# E21: Ingestion AI fallback on parse miss

## Outcome

When deterministic parsing misses or incompletely parses a Telegram listing, the owner
can request a Groq-backed listing proposal from `/admin/ingestion-issues`, review the
masked evidence-backed fields, and explicitly apply one proposal to create an offer.
Runs are minimized, expiring, and gated on the same fail-closed AI curation settings
used by place review and offer enrichment.

## Promoted tasks

- E21-T1: Parse issue ledger — `done` through PR #259
- E21-T2: Owner-triggered AI listing proposal from parse issues — `done` through PR #263 (`477d648`, migration `20260901_0018`)
