# Architecture

This domain owns system boundaries, dependency direction, runtime components, scale assumptions, and navigation to the architecture/dependency approval baseline.

## Canonical documents

- [System architecture](SYSTEM.md) — context, components, technology stack, repository shape, request/ingestion flows, security boundaries, tests, and scale triggers.
- [Dependency baseline](DEPENDENCY_BASELINE.md) — concise status, accepted-ADR summary, and pointer to the single full approval artifact.
- [Epic 0 architecture/dependency spike](../epics/E0-architecture-dependency-spike/SPIKE.md) — authoritative research and owner-approval artifact for the architecture/dependency baseline.

## Baseline

- Python/FastAPI owns backend and ingestion behavior; TypeScript/Next.js renders and localizes generated contracts.
- The backend is a package-by-feature modular monolith using interactors, presenters, service objects, and narrow ports/adapters.
- PostgreSQL/PostGIS is canonical storage.
- Docker Compose runs the system on one server. Shared Nginx/Certbot is the live public HTTPS edge under [ADR-020](../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md); the application-owned Caddy listener on `:3100` remains a rollback path.
- Added abstractions and dependencies need a demonstrated responsibility or implementation boundary.

Spike revision 2 and implementation-plan revision 3 are owner-approved. Proof or product code still proceeds only through the promoted task's state, dependency, dedicated-branch, review, and completion gates.
