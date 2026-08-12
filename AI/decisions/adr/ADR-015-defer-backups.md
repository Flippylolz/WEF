---
schema: ai-docs/adr@1
id: ADR-015
title: Defer backups and accept single-host data-loss risk
status: accepted
date: 2026-08-12
supersedes: [ADR-008]
superseded_by: []
resolves: []
---

# ADR-015: Defer backups and accept single-host data-loss risk

- Status: accepted for initial scope
- Date: 2026-08-12
- Decision: persist PostgreSQL/PostGIS, media, imports, and application secrets only on the supplied NUC; scheduled/off-server backups and restore drills are deferred.
- Rationale: the owner explicitly placed backup work out of scope.
- Consequence: disk failure, corruption, accidental deletion, host loss, or destructive migration can permanently lose all data. Documentation and readiness checks must not claim that data is backed up. Backup tasks remain a future reliability milestone rather than a public-launch gate.
- Supersedes: the off-server-backup requirements in [ADR-008](ADR-008-single-server-immutable-deployments.md).
