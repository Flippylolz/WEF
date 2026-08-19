---
schema: ai-workflow/task@1
id: E11-T1
epic: E11
title: "Implement scalable quick filters with last-day preset"
status: done
revision: 1
priority: P1
size: M
milestone: M3
dependencies: [E4-T2, E5-T2]
requirement_ids: [P-003]
decision_ids: [ADR-012, ADR-013]
branch:
  required: true
  name: feat/E11-T1-quick-filters
  task_id: E11-T1
  one_task_only: true
---

# E11-T1: Implement scalable quick filters with last-day preset

## Outcome

The map explorer exposes a quick-filter chip row backed by a server registry. The first preset filters offers published in the last 24 hours.

## Acceptance criteria

- [x] `GET /api/v1/quick-filters` lists presets with stable ids and label keys.
- [x] `quick_filter=last_day` resolves to a rolling 24-hour `published_from` on map and offer queries.
- [x] Quick filters conflict with explicit `published_from` and return 422.
- [x] Frontend loads presets from the API, toggles them in the URL, and clears manual publication dates when a preset is active.
- [x] Tests cover registry resolution and UI toggle behavior.
