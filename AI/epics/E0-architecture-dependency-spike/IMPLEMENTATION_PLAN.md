---
schema: ai-workflow/implementation-plan@1
epic: E0
title: "Architecture and dependency spike implementation plan"
status: approved
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E0-T1
    revision: 1
  - id: E0-T2
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T21:03:00Z"
  approved_revision: 2
  evidence: "Explicit owner approval in the current Cursor conversation: E0 implementation-plan revision 2"
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

- Task: [E0-T1 revision 1](tasks/E0-T1-review-architecture-and-dependency-proposal.md).
- Independent result: a documentation-only consistency review of spike revision 2, ADR-012, architecture, contracts, bootstrap boundaries, and dependency categories.
- Dependency: E1-T1 must be `done` first so this task can satisfy the mandatory dedicated-branch rule in an initialized safe repository.
- Tests: YAML/link/ID validation plus architecture/contract consistency review.
- Rollout: documentation only; material corrections return to the spike gate.

### 2. E0-T2 — Execute and lock the architecture proof

- Task: [E0-T2 revision 1](tasks/E0-T2-execute-and-lock-the-architecture-proof.md).
- Independent result: a synthetic backend-to-frontend vertical proof, dependency/runtime lockfiles, architecture checks, deterministic OpenAPI generation, PostGIS integration, i18n, Docker build evidence, and license/advisory evidence.
- Dependencies: E0-T1 and E1-T1 must both be `done`.
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

There is no deployment. Each task uses its own branch and pull request. E0-T2 starts only after E0-T1 and E1-T1 are complete and its gates are verified. If the proof fails, fix it within the approved scope or stop and invalidate the spike/plan when findings materially change architecture, dependencies, contracts, security, or deployment assumptions.

## Risks and mitigations

- **Bootstrap/branch cycle:** E0-T1 now depends on E1-T1 so the repository exists before its dedicated branch. E1-T1 remains the only repository bootstrap task.
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
- [x] Dependencies are acyclic and enforceable task by task; incomplete E1-T1 keeps both tasks blocked.
- [x] Modules, contracts, tests, migrations, risks, rollout, and rollback are explicit.
- [x] No deferred decision blocks this E0 scope.
- [x] No proposed task appears as an executable sequence; E0 candidates were moved to `tasks/`.
- [x] No production or disposable proof code is authorized by this draft.
- [x] Revision 2 received explicit owner approval and approval metadata matches this revision.

## Owner decision

Flippylolz explicitly approved implementation-plan revision 2 on 2026-08-12. The approval authorizes the recorded E0 task sequence and constraints, not immediate code: each task still requires a satisfied implementation gate, completed dependencies, `ready` state, and its own branch before becoming `in_progress`.
