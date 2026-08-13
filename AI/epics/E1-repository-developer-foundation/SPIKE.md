---
schema: ai-workflow/spike@1
epic: E1
title: "Repository and developer foundation research"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-001, ADR-005, ADR-008, ADR-009, ADR-010, ADR-012, ADR-013, ADR-017]
domain_docs: [architecture, governance, operations]
proposed_task_ids: [E1-T1, E1-T2, E1-T3, E1-T4, E1-T5, E1-T6, E1-T7]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T21:03:00Z"
  approved_revision: 2
  evidence: "Explicit owner approval in the current Cursor conversation: E1 spike revision 2"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Repository and developer foundation

> Revision 2 is owner-approved research. Implementation proceeds only through promoted tasks in the current approved implementation plan; this spike alone authorizes no code.

## Question

What repository, workspace, container-context, and CI foundation safely supports the accepted two-application modular monolith without admitting source data or weakening procedural governance?

## Context and constraints

- Repository safety/bootstrap E1-T1 is the only implementation that may precede the future E0 architecture proof, and it still requires this epic's own approvals before execution.
- The raw export, archives, media, databases, environment files, Telegram sessions, and sensitive reports must stay outside Git and Docker contexts.
- GitHub-enforced branch protection is cancelled under ADR-017; branch, pull-request, and CI controls remain procedural.
- E1-T2 must consume the accepted E0 proof rather than choose a competing architecture.

Governing domains:

- [Architecture](../../architecture/README.md)
- [Governance](../../governance/README.md)
- [Operations](../../operations/README.md)

Governing decisions and deferred gates:

- [ADR-001](../../decisions/adr/ADR-001-split-python-api-typescript-web.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-009](../../decisions/adr/ADR-009-feature-branch-development.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-017](../../decisions/adr/ADR-017-no-enforced-branch-protection.md)
- [D-007](../../decisions/deferred/D-007-github-protection-eligibility.md)

## Research method

Review repository/governance rules, the architecture and deployment boundaries, package-manager locking expectations, Docker-context risks, and the CI/OpenAPI contract requirements. Research remains Markdown-only.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- ADR-001 and ADR-012 require separate FastAPI and Next.js applications with backend-owned business behavior.
- ADR-013 requires deterministic committed OpenAPI plus offline CI documentation while production docs routes remain disabled.
- ADR-017 keeps branch/PR/check discipline but removes any claim of platform-enforced protection.
- The roadmap requires uv/pnpm lockfiles, PostGIS/Caddy Compose services, architecture checks, and synthetic-only CI.
- Owner-approved E0 spike revision 2 assigns root ignore files/README/environment example to E1-T1, measured Docker builds and lockfiles to E0-T2, application Dockerfiles/scaffolds to E1-T2, and local Compose to E1-T3.
- Current official Docker documentation confirms named multi-stage build stages, `.dockerignore`-controlled contexts, digest-pin policies, BuildKit secret mounts, long-syntax read-only mounts, named volumes, health-check dependency conditions, optional profiles, and project-name isolation without `container_name`.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Adopt a small monorepo with uv and pnpm workspaces, explicit app boundaries, locked runtimes, and narrowly scoped Compose/CI jobs.
- Separate repositories would increase contract and deployment coordination without addressing current scale.
- A broad generated platform scaffold would create executable code before approval and obscure source-data safety controls.

## Recommendation

Use a minimal reproducible monorepo, explicit ignore/build-context controls, accepted E0 boundaries, synthetic CI, and procedural governance. Keep E1-T5 cancelled unless ADR-017 is superseded.

For the requested repository bootstrap:

### E1-T1 repository safety and initial branch

- Bootstrap the empty remote with only a minimal root README on `main`, then configure `git@github.com:Flippylolz/WEF.git` as `origin`. Use SSH for Git fetches/pushes; this one-time base-ref bootstrap is not an ordinary direct feature commit.
- Carry the pre-existing approved `AI/` documentation on `docs/ai-documentation-foundation`, then create `chore/E1-T1-repository-safety` from that branch. E1-T1's commit boundary contains only `.gitignore`, `.dockerignore`, safe `.env.example`, and the full root `README.md`.
- `.gitignore` excludes `est-test/`, `est-test.tar.gz`, archives, media, environment/secrets, Telegram sessions, local databases, caches, coverage, build output, generated sensitive reports, and editor/OS noise. It does not ignore dependency lockfiles or `contracts/openapi/v1.json`.
- `.dockerignore` protects any root build context from Git metadata, source data/media, secrets, local databases, caches, and unrelated outputs. It is verified against the actual workspace before a build.
- The root README links `AI/README.md`, states that the repository is pre-implementation, documents prerequisites and source-data exclusions, and does not advertise commands or services that do not exist.
- `.env.example` contains safe names/comments only. It is not a production configuration source.
- No Dockerfile, Compose file, app scaffold, or Make target is included in E1-T1.

### E1-T2 application scaffold and starter Dockerfiles

- E1-T2 waits for completed E0-T2 and uses its accepted manifests, lockfiles, package boundaries, health behavior, and measured commands.
- Add the minimal backend/web scaffolds and named development/build/runtime Dockerfile targets on `feature/E1-T2-application-scaffold`.
- Runtime stages use locked installs, non-root users, explicit commands, and exclude development/documentation tools and source data.
- Introduce the root `Makefile` only when real application commands exist. It remains a thin façade for help/install/format/lint/type-check/test/contract/build commands and contains no business or environment-selection logic.

### E1-T3 local Compose

- E1-T3 waits for completed E1-T2 and runs on `feature/E1-T3-local-compose`.
- Add `infra/compose.yaml` only after web/API health commands exist. Include PostGIS, API, web, optional Caddy, and an on-demand importer using the backend image.
- Use a WEF-scoped project name, one internal network, named database/media volumes, no `container_name`, only the intended edge port, health-check dependency conditions, and a long-syntax read-only source mount available only to importer runs.
- Keep Telegram disabled until Epic 8. Use profiles for optional edge/operator services where they simplify the default path.
- Extend the existing Makefile with real Compose up/down/logs/build and importer dry-run targets; do not add no-op placeholders.

### Commit and branch boundary

The owner's request is not implemented as one branch or one initial commit because that would combine E1-T1, E0-T2, E1-T2, and E1-T3 and violate the accepted dependency/branch policy. Each task is prepared and reviewed independently in canonical order. No commit is created merely by approving this spike or a later implementation plan; commit creation remains an explicit task action.

This recommendation is complete for owner review but does not authorize any proposed task.

## Proposed task boundaries

- [E1-T1: Initialize repository safety](tasks/E1-T1-initialize-repository-safety.md) — promoted after spike approval; initial repository branch, ignores, safe environment example, root README, commit, and PR; no executable scaffold.
- [E1-T2: Scaffold web and backend applications](tasks/E1-T2-scaffold-web-and-backend-applications.md) — promoted; accepted E0 application scaffolds, named Docker targets, and the first real-command Make targets.
- [E1-T4: Establish CI baseline](tasks/E1-T4-establish-ci-baseline.md) — promoted; stable synthetic CI, contract checks, and commit-addressed artifacts.
- [E1-T3: Add local Docker Compose](tasks/E1-T3-add-local-docker-compose.md) — promoted; PostGIS/API/web/optional-edge/importer topology and real Compose Make targets.
- [E1-T5: Configure protected-main governance](proposed-tasks/E1-T5-configure-protected-main-governance.md) — cancelled traceability only.
- [E1-T6: Configure Dependabot update pull requests](proposed-tasks/E1-T6-configure-dependabot-update-pull-requests.md) — candidate boundary for spike refinement.
- [E1-T7: Implement scheduled Dependabot merge controller](proposed-tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md) — candidate boundary for spike refinement.

E1-T1, E1-T2, E1-T4, and E1-T3 are promoted in implementation-plan revision 4. E1-T5 remains cancelled; E1-T6 and E1-T7 remain non-actionable under `proposed-tasks/`.

## Risks and open questions

- A permissive ignore or build context could leak the export or Telegram sessions.
- Scaffolding before E0 approval could embed the wrong package boundaries.
- A write-capable dependency-update workflow could execute untrusted pull-request code; E1-T7 must retain its no-checkout design.
- E1-T1's unborn bootstrap branch needs an explicit remote/default-branch handoff before the normal “branch from latest main” rule can apply; the implementation plan must document that one-time sequence without claiming protected-main enforcement.
- Exact image/runtime versions and Dockerfile commands remain E0-T2 measured outputs; E1 must consume them rather than guess.
- Exact Compose profiles and Make targets follow actual E1-T2 commands and must not be placeholders.
- Resolve every named deferred-decision gate before promoting affected work.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] Proposed task scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] Repository, ignore, README, Dockerfile, Compose, Makefile, initial-branch, and commit boundaries are explicit.
- [x] No production or disposable proof code was created.
- [x] `revision: 2` represents the material content being submitted.
- [x] Revision 2 received explicit owner approval and approval metadata matches this revision.

## Owner decision

Flippylolz explicitly approved revision 2 on 2026-08-12. This approval permits task refinement/promotion and implementation planning only; it does not permit code.
