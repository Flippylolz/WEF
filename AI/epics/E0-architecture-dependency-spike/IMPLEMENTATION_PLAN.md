---
schema: ai-workflow/implementation-plan@1
epic: E0
title: "Architecture and dependency spike implementation plan"
status: approved
revision: 3
owner: owner
spike_revision: 2
task_sequence:
  - id: E0-T1
    revision: 2
  - id: E0-T2
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T21:03:00Z"
  approved_revision: 3
  evidence: "Explicit owner directive in the current Cursor conversation: do not wait for reviews; continue stacking PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Architecture and dependency spike

## Approved spike baseline

[E0 spike revision 2](SPIKE.md) was explicitly approved by Flippylolz on 2026-08-12. It binds this plan to:

- backend-owned domain/application behavior and a thin generated-contract frontend;
- package-by-feature modular-monolith dependency direction;
- explicit interactors, presenters, domain/application services, ports/adapters, and transaction ownership;
- the proposed dependency inventory and measured-proof acceptance;
- strict source-data, secret, Docker-context, and non-production boundaries; and
- separate ownership/branches for repository safety, the architecture proof, application scaffolding, and Compose.

The spike approval permits this plan and task promotion only. No task may start until this plan's current revision is separately approved and its task gates are satisfied.

## Scope and outcome

Implementation will start from a reviewed backend-centric modular-monolith proof and reproducible dependency lockfiles, not ad hoc framework choices.

This plan includes only:

- reviewing and recording the approved architecture/dependency baseline in E0-T1; and
- implementing the bounded synthetic proof and locking measured dependencies in E0-T2.

It excludes product features, real source data/media, local multi-service Compose, production deployment, Telegram integration, and any E1 implementation.

## Ordered task sequence

### 1. E0-T1 — Review architecture and dependency proposal

- Task: [E0-T1 revision 2](tasks/E0-T1-review-architecture-and-dependency-proposal.md).
- Independent result: a documentation-only consistency review of spike revision 2, ADR-012, architecture, contracts, bootstrap boundaries, and dependency categories.
- Dependency: E1-T1 has an open ancestor PR. Under ADR-018, E0-T1 branches from it and may proceed with `dependency_gate: stacked`; it cannot be completed or merged until E1-T1 is `done`.
- Tests: YAML/link/ID validation plus architecture/contract consistency review.
- Rollout: documentation only; material corrections return to the spike gate.

### 2. E0-T2 — Execute and lock the architecture proof

- Task: [E0-T2 revision 2](tasks/E0-T2-execute-and-lock-the-architecture-proof.md).
- Independent result: a synthetic backend-to-frontend vertical proof, dependency/runtime lockfiles, architecture checks, deterministic OpenAPI generation, PostGIS integration, i18n, Docker build evidence, and license/advisory evidence.
- Dependencies: after E0-T1 opens its direct child PR, E0-T2 may branch from E0-T1 under ADR-018 without waiting for reviews. It cannot be completed or merged until E0-T1 and E1-T1 are `done`.
- Affected modules/contracts: future backend/web proof modules, manifests/lockfiles, `contracts/openapi/v1.json`, architecture import contracts, and E0 conclusion documents.
- Tests: unit, PostGIS integration, import-linter negative contract, OpenAPI/Redocly/`oasdiff`, generated client compile/request, thin frontend rendering/i18n, clean install/build, image/context inspection, and dependency/license/advisory scans.
- Rollout: no production rollout; accepted proof becomes E1-T2's scaffold baseline. Material architecture or contract changes return to the spike.

## Cross-task architecture

E0-T1 changes documentation only. E0-T2 must demonstrate the inward dependency direction `interface -> application -> domain`, with infrastructure implementing application/domain-owned ports and composition-root wiring kept outside features. Routes and presenters contain no domain decisions; SQLAlchemy mappings remain infrastructure; the frontend consumes generated OpenAPI types and renders backend-provided decisions.

E0-T2 uses synthetic entities only and owns no production migration. The proof may create disposable test schema state inside isolated test PostGIS, but it must not create or migrate production data.

## Data and migrations

- No raw export, archive, media, contact, user, credential, Telegram session, or production database is read or copied.
- Synthetic fixtures contain no source-derived payload.
- Any Alembic example is confined to the synthetic proof and must be forward reproducible from an empty test database.
- There is no backup/recovery promise; no production data exists in this epic.

## Security and privacy

- `.gitignore` and `.dockerignore` protections delivered by E1-T1 are prerequisites.
- Docker contexts and runtime layers are inspected for source data, media, credentials, production values, and documentation-only tooling.
- Build credentials, if required, use ephemeral BuildKit secrets rather than arguments, environment, files, or caches.
- Production OpenAPI/Swagger/ReDoc routes remain disabled.
- Logs and test failures contain synthetic data only.

## Test and verification strategy

- E0-T1: documentation links, YAML schemas, IDs/revisions, and architecture/contract consistency.
- E0-T2 backend: unit tests, strict typing/linting, architecture import contracts, and PostGIS integration.
- E0-T2 contract: deterministic OpenAPI diff, Redocly lint/static artifact, `oasdiff`, and generated TypeScript compile/request.
- E0-T2 frontend: thin projection rendering and `next-intl` Server/Client behavior without domain-rule recomputation.
- E0-T2 supply chain/build: reproducible `uv`/`pnpm` locks, clean installs, license/advisory scans, Docker builds, and image/context inspection.

## Operations, rollout, and rollback

There is no deployment. Each task uses its own branch and pull request. Approved implementation continues as an ordered stack without waiting for review: E1-T1 → E0-T1 → E0-T2. Each child targets its immediate parent branch, and the stack merges only from the base upward after reviews and CI. If the proof fails, fix it within the approved scope or stop and invalidate the spike/plan when findings materially change architecture, dependencies, contracts, security, or deployment assumptions.

## Risks and mitigations

- **Stack drift:** record parent PR/head evidence, refresh descendants after material parent changes, and retarget in base-first merge order.
- **Over-broad proof:** enforce the synthetic acceptance list and exclude real product/import/deployment work.
- **Dependency churn:** lock only after clean measured installs/tests; record license, advisory, purpose, and replacement path.
- **Boundary erosion:** import-linter includes a deliberate failing example and CI makes the architecture contract visible.
- **Leaked source/secrets:** rely on E1-T1 safety files, synthetic fixtures, context inspection, and secret scans.
- **Docker placeholders becoming product architecture:** Docker builds use the actual proof commands; Compose remains E1-T3.

## Invalidation triggers

Return to the spike when backend/frontend ownership, dependency direction, package boundaries, public/persisted contracts, security, data handling, deployment topology, or the dependency category recommendation changes materially.

Return to this plan when the approved spike remains valid but task scope, order, dependencies, modules, acceptance, tests, or rollback changes.

## Approval checklist

- [x] Spike revision 2 has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria and traceability.
- [x] Dependencies are acyclic and enforceable through ADR-018 stacked gates; incomplete dependencies still block completion and merge.
- [x] Modules, contracts, tests, migrations, risks, rollout, and rollback are explicit.
- [x] No deferred decision blocks this E0 scope.
- [x] No proposed task appears as an executable sequence; E0 candidates were moved to `tasks/`.
- [x] This approved plan authorizes only its promoted task sequence; it does not bypass any task state, dependency, branch, review, or completion gate.
- [x] Revision 3 received explicit owner approval through the owner's continue-stacking directive.

## Owner decision

Flippylolz explicitly approved implementation-plan revision 3 on 2026-08-12 by directing implementation to continue through stacked pull requests without waiting for reviews. Each task still requires approved gates, a valid satisfied/stacked dependency gate, `ready` state, and its own branch before becoming `in_progress`; no child may complete or merge before its dependencies.
