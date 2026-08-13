# Architecture and Dependency Baseline

## Authoritative approval artifact

The complete architecture/dependency research, dependency inventory, proof scope, acceptance criteria, risks, and owner-decision fields live in the [Epic 0 architecture/dependency spike](../epics/E0-architecture-dependency-spike/SPIKE.md). That spike is the single approval artifact; this document does not copy or supersede it.

## Current status

- Epic: [E0 — Architecture and dependency spike](../epics/E0-architecture-dependency-spike/README.md), currently `in_progress` through an ADR-018 stack above E1-T1.
- Spike artifact: revision 2, explicitly owner-approved and research-only. The revision includes repository, container bootstrap, Makefile, root README, task-ownership, and branch boundaries.
- Implementation plan: [revision 3 owner-approved](../epics/E0-architecture-dependency-spike/IMPLEMENTATION_PLAN.md), allowing ordered stacked implementation under ADR-018 without relaxing merge/completion gates.
- Promoted proof task: [E0-T2](../epics/E0-architecture-dependency-spike/tasks/E0-T2-execute-and-lock-the-architecture-proof.md), `in_progress` in the ordered stack with measured results in the [proof report](../epics/E0-architecture-dependency-spike/PROOF_REPORT.md). Its dependency gate remains `stacked` until E1-T1 and E0-T1 integrate.
- Governing lifecycle: [approval-gated workflow](../workflow/README.md).

## Accepted ADR baseline

The [decision registry](../decisions/README.md) is authoritative for status and supersession:

- [ADR-001](../decisions/adr/ADR-001-split-python-api-typescript-web.md): split Python/FastAPI backend and ingestion from the TypeScript/Next.js web application.
- [ADR-005](../decisions/adr/ADR-005-postgresql-postgis.md): use PostgreSQL/PostGIS as canonical storage.
- [ADR-012](../decisions/adr/ADR-012-backend-centric-modular-monolith.md): use a backend-centric package-by-feature modular monolith with interactors, presenters, narrow ports/adapters, and enforced dependency direction.
- [ADR-013](../decisions/adr/ADR-013-committed-openapi-offline-docs.md): commit deterministic OpenAPI, generate frontend contracts, and keep production API documentation routes disabled.
- [ADR-016](../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md): use pseudonymous username/password accounts and an owner-only administration console.
- [ADR-017](../decisions/adr/ADR-017-no-enforced-branch-protection.md): keep branch/PR/CI governance procedural without claiming platform-enforced `main` protection.

Dependency versions, licenses, advisories, proof measurements, and evaluated substitutions are recorded in the E0 proof report and committed lockfiles. This pointer does not supersede those artifacts or authorize later product tasks.
