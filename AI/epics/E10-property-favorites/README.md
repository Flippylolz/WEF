---
schema: ai-workflow/epic@1
id: E10
title: "Property favorites"
status: ready
milestones: [M3]
owner: owner
---

# E10: Property favorites

## Outcome

Signed-in users can star grouped map locations, review them from a toolbar control next to the profile button, and jump back to starred locations from a favorites dialog.

## Promoted tasks

- [E10-T1: Implement property favorites](tasks/E10-T1-implement-property-favorites.md) — P1/M, M3; depends on E9 account modal and E6-T4 auth API.

## API

- `GET /api/v1/favorites`
- `PUT /api/v1/favorites/{location_id}`
- `DELETE /api/v1/favorites/{location_id}`
