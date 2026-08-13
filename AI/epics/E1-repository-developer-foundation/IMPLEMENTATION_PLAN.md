---
schema: ai-workflow/implementation-plan@1
epic: E1
title: "Repository and developer foundation implementation plan"
status: approved
revision: 4
owner: owner
spike_revision: 2
task_sequence:
  - id: E1-T1
    revision: 3
  - id: E1-T2
    revision: 2
  - id: E1-T4
    revision: 1
  - id: E1-T3
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T22:07:21Z"
  approved_revision: 4
  evidence: "Owner directive to prepare the MVP/autodeploy, choose safe defaults, log decisions/blockers, and continue stacking PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Repository and developer foundation

## Approved spike baseline

[E1 spike revision 2](SPIKE.md) was explicitly approved by Flippylolz on 2026-08-12. It separates repository safety, application/Dockerfile scaffolding, CI, and Compose into independent tasks and branches.

Revision 4 preserves the completed/open repository-safety bootstrap and authorizes the already-spiked application scaffold, CI baseline, and local Compose boundaries needed for the MVP stack. E1-T5 stays cancelled; E1-T6 and E1-T7 remain proposed.

## Scope and outcome

Create a reproducible Git/GitHub and local-development baseline that cannot accidentally commit or package the source archive/media:

- initialize the empty repository and canonical remote;
- create a minimal root-README commit on `main`, because empty commits are not allowed and GitHub needs a base ref;
- put all existing `AI/**` documentation on `docs/ai-documentation-foundation` and open a PR to `main`;
- stack `chore/E1-T1-repository-safety` on the documentation branch;
- add `.gitignore`, `.dockerignore`, `.env.example`, and a concise root `README.md`;
- commit and push the task branch and open its PR against the documentation branch; and
- consume E0-T2's accepted backend/web proof as the application scaffold;
- provide real-command Make targets and named development/build/runtime images;
- generalize CI into stable backend/frontend/contract/image checks and commit-addressed artifacts;
- provide isolated local Compose for PostGIS, API, web, optional Caddy, and an on-demand importer; and
- continue each result as an ordered stacked PR without silently merging descendants.

Production deployment, live/source ingestion, product features, Dependabot configuration/controller, authentication, and Telegram remain excluded from this revision.

## Ordered task sequence

### 1. E1-T1 — Initialize repository safety

- Task: [E1-T1 revision 3](tasks/E1-T1-initialize-repository-safety.md).
- Dependencies: none.
- Branch: `chore/E1-T1-repository-safety`.
- Independent result: root ignore/environment/README safety baseline committed on one task branch and proposed through one stacked PR after the pre-existing documentation gets its own PR.
- GitHub bootstrap: because the remote is empty, create/push a minimal root-README commit on `main`. Put the existing AI documentation on `docs/ai-documentation-foundation` with a PR to `main`, then branch E1-T1 from it and target the stacked PR back to the documentation branch.
- Verification: Git ignore/staging inspection, Docker-context candidate inspection, Markdown/link/lint checks, remote/branch checks, and PR base/head/file review.

### 2. E1-T2 — Scaffold web and backend applications

- Task: [E1-T2 revision 2](tasks/E1-T2-scaffold-web-and-backend-applications.md).
- Dependency: E0-T2 is an open direct ancestor PR under ADR-018; it must be `done` before E1-T2 completes/merges.
- Branch: `feature/E1-T2-application-scaffold`.
- Independent result: E0's accepted proof becomes the minimal application scaffold with named development/build/runtime image targets and a thin root Makefile backed only by real commands.
- Verification: frozen clean installs, direct development/runtime smoke checks, format/lint/type/test/contract targets, safe-context image builds, and runtime-content inspection.

### 3. E1-T4 — Establish CI baseline

- Task: [E1-T4 revision 1](tasks/E1-T4-establish-ci-baseline.md).
- Dependency: E1-T2; it may proceed as E1-T2's direct stack child.
- Branch: `ci/E1-T4-baseline`.
- Independent result: stable synthetic backend/frontend/contract/image jobs, documentation-link checks, deliberate failure evidence, and commit-addressed OpenAPI artifacts.
- Verification: workflow lint, successful GitHub checks, generated-contract drift/break probes, and no source/production credentials.

### 4. E1-T3 — Add local Docker Compose

- Task: [E1-T3 revision 2](tasks/E1-T3-add-local-docker-compose.md).
- Dependency: E1-T2; E1-T4 remains in direct ancestry for ordered review but is not a functional prerequisite.
- Branch: `feature/E1-T3-local-compose`.
- Independent result: project-isolated PostGIS/API/web/optional-Caddy topology with named persistence, health gates, and importer-only read-only source access.
- Verification: rendered configuration, same-origin smoke, no unintended published ports, persistence recreation check, and source-mount writability check.

## Affected files and systems

- Existing `AI/**` documents, committed independently on `docs/ai-documentation-foundation`.
- New root `.gitignore`, `.dockerignore`, `.env.example`, and `README.md`.
- Existing accepted `apps/backend`, `apps/web`, root manifests/lockfiles, OpenAPI contract, and Dockerfiles from E0-T2.
- Root `Makefile`, stable `.github/workflows/**`, and commit-addressed contract artifacts.
- `infra/compose.yaml`, local WEF-scoped networks/volumes, and optional Caddy configuration.
- Local `.git` metadata.
- GitHub `Flippylolz/WEF` main/head refs and two unmerged pull requests.

No production host, real source dataset, production migration/data, authentication surface, or Telegram session is changed.

## Safety and privacy

- Ignore the raw `est-test/` tree, `est-test.tar.gz`, archives, media, environment/secrets, Telegram sessions, local databases, caches, coverage, build outputs, and sensitive generated reports.
- Keep dependency lockfiles and the future committed OpenAPI contract eligible for version control.
- `.env.example` contains safe names/comments only; Compose derives local service URLs from explicit non-production values.
- Verify candidates before staging and staged content before commit.
- Runtime images remain non-root and exclude source data, media, credentials, development/documentation tools, and build secrets.
- Compose does not mount the source export into API/web; only the explicit importer profile gets a read-only mount.

## Commit and pull-request plan

E1-T1's existing bootstrap history is preserved. Create E1-T2 from E0-T2, E1-T4 from E1-T2, and E1-T3 from E1-T4. Each branch contains one task and targets its immediate parent. Record every PR/head in dependency evidence. Merge/integrate base-first only; never force-push shared history or merge a child before its parent.

## Test and verification strategy

- `git check-ignore`/status/staged diff for representative sensitive paths and intended files.
- E1-T2: frozen installs, Make target checks, direct/container smoke tests, safe-context builds, and runtime image inspection.
- E1-T4: action/workflow lint, GitHub checks, synthetic PostGIS, architecture negative proof, contract drift/break probes, docs links, and artifact inspection.
- E1-T3: `docker compose config`, health/same-origin smoke, port inspection, database-volume recreation, and importer-only read-only source mount.
- All tasks: Markdown links/lints, secret/source-data candidate inspection, and PR base/head/file isolation.

## Rollout and rollback

There is no production rollout. External effects are GitHub refs/PRs/checks and local Docker resources scoped to WEF. Before merge, rollback closes the affected PR/branch and removes only WEF-owned local containers/networks/volumes when needed. After merge, use normal reverts; never rewrite shared history.

## Risks and mitigations

- **Source/secret leak:** strict ignore files plus pre-stage and staged-diff inspection.
- **No PR base in an empty repository:** one minimal README bootstrap commit on `main`; pre-existing docs and E1-T1 then use separate/stacked PRs.
- **Stacked diff contamination:** branch E1-T1 from the documentation branch and target its PR to that branch, then verify changed files.
- **Proof/scaffold duplication:** E1-T2 refines E0-T2 in place and does not introduce competing manifests, versions, or architecture.
- **Placeholder Make/Compose commands:** every target maps to a verified real command; Compose waits for E1-T2 health and image targets.
- **CI drift:** stable named checks share frozen lockfiles and deterministic OpenAPI generation; negative probes prove gates fail.
- **Local host interference:** project-scoped resources, no `container_name`, only one configurable edge port, and no non-WEF resource mutation.
- **False branch-protection claim:** ADR-017 remains authoritative; use procedural review/checks only.
- **Accidental merge:** PR creation is in scope, merge is not.

## Invalidation triggers

Return to the E1 spike if repository ownership, branch/PR policy, source-data boundaries, architecture, or task split changes materially. Return to this plan if the approved spike remains valid but task order, files, checks, local topology, branch evidence, or rollback changes.

## Approval checklist

- [x] E1 spike revision 2 has explicit owner approval and remains valid.
- [x] E1-T1 revision 3 and E1-T2/E1-T3 revision 2 plus E1-T4 revision 1 are promoted with complete acceptance and traceability.
- [x] Dependencies are acyclic and may proceed through recorded ADR-018 ancestry without relaxing completion/merge gates.
- [x] Files, Git/GitHub/local-Docker effects, safety checks, risks, rollout, and rollback are explicit.
- [x] No deferred decision blocks the scaffold, CI, or local Compose scope.
- [x] No proposed task appears as an executable sequence.
- [x] Production deployment, real data, authentication, Telegram, and dependency automation remain excluded.
- [x] Revision 4 received explicit owner approval through the overnight MVP/autodeploy/continue-stacking directive.

## Owner decision

Flippylolz approved implementation-plan revision 4 on 2026-08-12 by directing the agent to prepare the MVP/autodeploy, choose and log safe defaults instead of waiting for questions, and continue stacking PRs. This authorizes E1-T2, E1-T4, and E1-T3 within the approved E1 spike boundaries. It does not authorize production deployment changes in this epic, destructive host actions, real-source ingestion, credential invention, child-before-parent merge, or bypass of test/review gates.
