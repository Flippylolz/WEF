---
schema: ai-docs/adr@1
id: ADR-007
title: Use local mounted media first, behind a storage interface
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-007: Use local mounted media first, behind a storage interface

- Status: accepted for MVP
- Date: 2026-08-12
- Decision: keep media on a server-mounted volume and expose it through a storage interface and controlled HTTP path.
- Rationale: approximately 2.7 GB of extracted photos and videos is manageable on one server and does not initially justify object-storage operations.
- Consequence: media is never copied into Git or application images. The database stores storage keys rather than host paths so migration to S3-compatible storage remains possible.
