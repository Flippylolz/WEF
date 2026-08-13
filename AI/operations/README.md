# Operations

This domain owns deployment behavior, production-host constraints, configuration transfer, persistence, observability, health verification, rollback, and server handoff evidence.

## Canonical documents

- [Deployment](DEPLOYMENT.md) — local/production environments, images, Compose/Caddy topology, CI/CD, configuration, health checks, rollback, and readiness.
- [Production server](SERVER.md) — inspected host capacity, workloads, ports, paths, permissions, persistence, transfer, and non-interference checks.
- [Rollback rehearsal](ROLLBACK_REHEARSAL.md) — healthy activation, reviewed failure injection, restoration evidence, and enable/abort gates.
- [Blocker log](BLOCKERS.md) — unresolved overnight blockers, owner inputs, safe workarounds, and resolved constraints.

## Non-negotiable constraints

- GitHub Actions variables hold non-secret production values and GitHub Actions secrets hold sensitive values. Together they are the deployment configuration source of truth.
- Every deploy transfers a complete validated release configuration, activates it atomically, and commits no production `.env`.
- Deploy immutable SHA-tagged images through GitHub Actions/GHCR/SSH to the isolated `/home/nuc/wef` runtime.
- Existing host workloads must not be disrupted.
- PostgreSQL, media, imports, and secrets persist on the NUC, but backups and restore drills are deferred. This is a single-host failure domain, not a recovery guarantee.
- Rollback guarantees cover compatible application images; data rollback is not guaranteed without backups.

Operational changes must include health verification, rollback/recovery notes, secret-handling review, and owner involvement for unavoidable privileged host changes.
