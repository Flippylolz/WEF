---
schema: ai-docs/adr@1
id: ADR-012
title: Use a backend-centric modular monolith
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-012: Use a backend-centric modular monolith

- Status: accepted as the architecture spike baseline
- Date: 2026-08-12
- Decision: keep business rules and display projections in a Python modular monolith organized by feature with domain, application, infrastructure, and interface boundaries. Use interactors, query services, domain/application service objects, ports/adapters, unit-of-work transaction boundaries, and presenters. The Next.js frontend primarily renders/localizes generated OpenAPI contracts and manages presentation state.
- Rationale: filtering, grouping, visibility, auth, masking, geocoding, and ingestion rules must remain consistent across browser, import, and future Telegram paths. A thin frontend and one backend implementation minimize rule drift while preserving clear replaceable boundaries.
- Consequence: routes and presenters contain no business decisions, interactors return application DTOs rather than ORM/HTTP objects, infrastructure implements inward-owned ports, and `import-linter` plus contract tests enforce dependency direction. Generic base repositories/services, frontend domain duplication, microservices, and a third-party DI container are rejected for the MVP.
- Detailed spike: [Epic 0 architecture/dependency spike](../../epics/E0-architecture-dependency-spike/SPIKE.md).
