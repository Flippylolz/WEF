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
- E21-T3: Link parse issues to applied offers — `done` through PR #267 (`e6d5b85`)
- Groq apply hardening (aliases, evidence tolerance) — `done` through PR #268–#271 (`89c940f`)

## Production recovery (2026-09-01)

Four parse misses on `wef_hist_candidate` were recovered via `/admin/ingestion-issues`
generate/apply; three gained map pins after worker geocode, one (Serock) remains
`needs_review` off-map by design. Operator notes: [UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md](../../ingestion/UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md#e21-ingestion-ai-parse-recovery-2026-09-01).
Batch CLI (`wef-batch-ingestion-ai-parse`, `wef-backfill-parse-issues`):
[OPERATOR_COMMANDS.md](../../operations/OPERATOR_COMMANDS.md#parse-issue-ledger-e21).
