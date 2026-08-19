---
schema: ai-workflow/task@1
id: E10-T1
epic: E10
title: "Implement property favorites"
status: done
revision: 1
priority: P1
size: M
milestone: M3
dependencies: [E6-T4, E9-T1]
branch:
  required: true
  name: feat/E10-T1-property-favorites
  task_id: E10-T1
  one_task_only: true
---

# E10-T1: Implement property favorites

## Acceptance criteria

- [x] Authenticated users can star and unstar accepted public locations.
- [x] Star control appears in the location list when signed in.
- [x] Toolbar star button opens a favorites dialog beside the profile control.
- [x] Favorites persist in `favorite_locations` with migration `20260820_0010`.
- [x] Tests cover favorites HTTP flows.
