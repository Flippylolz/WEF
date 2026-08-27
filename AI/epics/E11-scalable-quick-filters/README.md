---
schema: ai-workflow/epic@1
id: E11
title: "Scalable quick filters"
status: done
milestones: [M3]
owner: owner
---

# E11: Scalable quick filters

## Outcome

Visitors can apply server-defined publication quick filters such as “Last 24 hours” without manually editing date fields. New presets can be added by extending one backend registry and corresponding i18n label keys.

## Design

- Backend owns the preset registry in `catalog/application/quick_filters.py`.
- `GET /api/v1/quick-filters` exposes stable preset identifiers and label keys.
- Map and offer queries accept `quick_filter=<id>`; the backend resolves the cutoff timestamp.
- Manual `published_from` and `quick_filter` are mutually exclusive.
- Frontend renders presets from the API as toggle chips and stores the active preset in the URL.
- The visitor-relative “New since last visit” shortcut is browser-local rather
  than a server preset: the web app records visit-start timestamps in Web
  Storage and applies the prior visit as an explicit `published_from` value.
  The first visit records a baseline and leaves the shortcut disabled until the
  next browser session.

## Promoted tasks

- [E11-T1: Implement scalable quick filters with last-day preset](tasks/E11-T1-implement-scalable-quick-filters.md) — P1/M, M3

## Adding a new preset

1. Append one `QuickFilterPreset` entry to `list_quick_filter_presets()` and implement its resolver branch.
2. Add the `_QUICK_FILTER_IDS` allowlist entry.
3. Add an English label under `map.quickFilter.*` in `apps/web/messages/en.json`.
4. Extend unit tests in `tests/test_quick_filters.py`.

No frontend code changes are required beyond the label catalog when the preset list comes from the API.
