---
schema: ai-workflow/task@1
id: E12-T1
epic: E12
title: "Add catalog query indexes from audit"
status: done
revision: 1
priority: P1
size: M
milestone: M3
dependencies: [E3-T1, E4-T2]
requirement_ids: [P-001]
decision_ids: [ADR-005, ADR-012]
branch:
  required: true
  name: feat/E12-T1-database-indexes
  task_id: E12-T1
  one_task_only: true
---

# E12-T1: Add catalog query indexes from audit

## Outcome

Migration `20260819_0009` adds reviewed catalog indexes and documents the audit in `INDEX_AUDIT.md`.

## Acceptance criteria

- [x] Audit document lists reviewed tables, existing indexes, and gaps.
- [x] Additive Alembic migration creates `ix_offers_location_visible_published` and `ix_offers_visible_price_range`.
- [x] SQLAlchemy models mirror the migration indexes.
- [x] `EXPECTED_DATABASE_REVISION` advances to `20260819_0009`.
- [x] Migration replay tests pass on a fresh database.
