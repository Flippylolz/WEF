---
schema: ai-docs/adr@1
id: ADR-008
title: Deploy immutable images to one server
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: [ADR-015]
resolves: []
---

# ADR-008: Deploy immutable images to one server

- Status: deployment model accepted; backup consequence superseded by [ADR-015](ADR-015-defer-backups.md)
- Date: 2026-08-12
- Decision: GitHub Actions builds SHA-tagged images, publishes them to GHCR, and deploys a Docker Compose release over SSH to a single Linux server.
- Rationale: this is sufficient for fewer than 10,000 users and preserves a simple rollback path.
- Consequence: deployment uses the supplied non-root `nuc` account with a dedicated project-scoped SSH key, `/home/nuc/wef` persistence, and enough disk for database, media, and at least two image releases. [ADR-015](ADR-015-defer-backups.md) later removed the backup requirement.
