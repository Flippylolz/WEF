---
schema: ai-docs/deferred-decision@1
id: D-002
title: Recurring geocoding provider
status: resolved
task_gates: []
resolved_by:
  - E8-T4
---

# D-002: Recurring geocoding provider

- Status: **resolved** by [E8-T4](../../epics/E8-telegram-live-ingestion/tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) under AD-032 (2026-08-21).
- Recurring provider: **Geoapify** (same provider-neutral port/cache as ADR-021 historical import).
- Dated recheck (https://www.geoapify.com/pricing/ , 2026-08-21): free plan 3,000 credits/day, ≤5 rps, commercial use allowed with required attribution; WEF soft caps remain 2,700 credits/day and 4 rps.
- Public Nominatim: **not** allowed for recurring/always-on jobs (one-time seed policy unchanged).
- Fallback: **defer** on quota/rate/transient errors; no automatic provider fan-out.
- Paid plan activation still requires a separate owner decision if free soft limits become insufficient.
- Operator evidence: `wef-revalidate-recurring-geocoder` and optional `--live-check` (one credit via existing readiness path).
