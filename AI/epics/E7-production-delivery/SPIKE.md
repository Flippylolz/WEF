---
schema: ai-workflow/spike@1
epic: E7
title: "Docker/GitHub production delivery research"
status: approved
revision: 3
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-005, ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-015, ADR-017, ADR-018, ADR-019, ADR-020]
domain_docs: [operations, governance, security, data]
proposed_task_ids: [E7-T1, E7-T2, E7-T3, E7-T4, E7-T5, E7-T6, E7-T7, E7-T8, E7-T9, E7-T10]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-13T19:32:59Z"
  approved_revision: 3
  evidence: "Owner accepted the attached E7 Shared TLS Stack plan and selected the three-task E7 shared Nginx/TLS split"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Docker/GitHub production delivery

> Revision 3 is approved research. The spike remains non-executable; implementation requires the approved plan and individually promoted tasks.

## Revision 3 change control

[ADR-020](../../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md) selects Nginx and Certbot as the shared public edge for WEF and AI Forecast. Revision 3 preserves completed E7-T1 through E7-T4 as the Caddy-based anonymous rehearsal, then splits the shared-edge migration into an inert topology, reversible automation, and a live rollout. D-009 gates only the live rollout; it does not prevent locally proving configuration and rollback automation with synthetic fixtures.

## Question

How should a separately managed Nginx/Certbot edge be built, integrated, and rolled out on the supplied shared NUC without coupling ordinary WEF releases to AI Forecast or risking either application?

## Context and constraints

- GitHub Actions variables/secrets are the complete deploy-configuration source of truth; validated configuration is transferred atomically and never committed.
- The isolated wef-production Compose project uses /home/nuc/wef persistence and initially publishes only configurable port 3100.
- Existing AI Forecast, DuckDNS, and WireGuard workloads and ports 3000/TCP, 8080/TCP, and 51820/UDP must remain unchanged.
- The current Caddy/3100 and AI Forecast/3000 listeners remain rollback paths until live dual-host HTTPS evidence passes.
- The shared edge owns only ports 80/443, its dedicated project/path, Nginx configuration, bounded logs, ACME webroot, and complete persistent Certbot state.
- Two owner-approved hostnames and confirmed public 80/443 forwarding remain unresolved under D-009 and block live rollout only.
- Backups/restore drills are deferred under ADR-015; rollback covers compatible application releases, not guaranteed data restoration.
- ADR-019 bounds the first release to anonymous synthetic browsing over interim HTTP. Sensitive source data, registration, sessions, administration, contact reveal, and Telegram are disabled.
- GitHub Actions currently fails before job creation under B-006. Implementation must still produce locally testable release artifacts/workflows, but cannot claim hosted delivery operational until GitHub starts a release run.

Governing domains:

- [Operations](../../operations/README.md)
- [Governance](../../governance/README.md)
- [Security](../../security/README.md)
- [Data](../../data/README.md)

Governing decisions and deferred gates:

- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-009](../../decisions/adr/ADR-009-feature-branch-development.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-014](../../decisions/adr/ADR-014-actions-owned-deploy-configuration.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [ADR-017](../../decisions/adr/ADR-017-no-enforced-branch-protection.md)
- [ADR-018](../../decisions/adr/ADR-018-ordered-stacked-pull-requests.md)
- [ADR-019](../../decisions/adr/ADR-019-anonymous-http-production-rehearsal.md)
- [ADR-020](../../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md)
- [D-001](../../decisions/deferred/D-001-production-server-domain.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)
- [D-009](../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md)

## Research method

Review the inspected server baseline, current Compose/Caddy topology, ADR-020, Nginx virtual-host and reload behavior, Certbot webroot/renewal hooks, Docker Compose external networks, secret/config transfer, migration order, and independent rollback of WEF and AI Forecast.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Evidence

- D-001 now records the selected NUC/DuckDNS/port and ADR-019 separates interim anonymous HTTP from the later HTTPS gate.
- ADR-010 requires WEF isolation; ADR-014 assigns deploy configuration to Actions; ADR-017 keeps main/PR rules procedural.
- The roadmap requires merged-PR-origin verification, AUTO_DEPLOY_ENABLED, immutable SHA/digest images, locked deployment, health smoke tests, and resumable archive transfer.
- Read-only host inspection confirms Docker/Compose access without sudo, ample initial disk, existing projects on 3000/8080/51820, and writable `/home/nuc`.
- Current Docker documentation supports explicit production Compose files, internal networks, health-gated dependencies, un-published `expose`, and environment files.
- Current GitHub Actions guidance supports branch-filtered push/workflow dispatch, minimum job permissions, GHCR publication with `packages: write`, immutable build outputs, repository variables/secrets, and workflow concurrency.
- The production boundary can be fully modeled and tested locally before touching the host. Hosted Actions and the public router path require live verification and remain evidence gates rather than assumptions.
- Current Nginx documentation supports name-based HTTPS virtual servers, explicit proxy headers, `nginx -t` file/syntax validation, and graceful configuration replacement in which a failed activation retains the old workers.
- Current Certbot documentation supports non-interactive webroot issuance, renewal reuse of saved authenticator settings, `renew --dry-run`, and deploy hooks that run only after successful renewal.
- Current Docker Compose documentation supports a separately managed external network, read-only configuration mounts, health checks, persistent volumes, and config rendering before activation.

## Options to evaluate

- Use one isolated Compose project with immutable images, Actions-owned complete configuration, verified SSH, health-gated activation, retained previous release, and explicit rollback.
- Build on the server or mutate a shared Compose project, which weakens reproducibility and non-interference.
- Claim backups from persistent volumes, which contradicts ADR-015.
- Put Nginx inside the ordinary WEF project, which would let routine WEF releases recreate shared AI Forecast ingress and violates ADR-020 isolation.
- Replace both application listeners in one irreversible step, which creates a shared failure domain and removes independent rollback.

## Approved recommendations

Revision 2 promoted E7-T1 through E7-T4 as an ordered stack for the anonymous synthetic rehearsal:

1. E7-T1 adds a self-contained production Compose/Caddy topology and host-safe deploy/preflight/smoke/rollback scripts. It has no server side effect.
2. E7-T2 creates only `/home/nuc/wef`, records before/after inventories, validates port/capacity/permissions, and rehearses the topology without changing existing projects.
3. E7-T3 publishes SHA-tagged application images and adds a main-only/manual, merged-PR/enable-gated, locked GitHub deployment workflow with complete atomic configuration transfer.
4. E7-T4 performs a healthy release and deliberate unhealthy-release rollback rehearsal before enabling automatic deployment.

Keep E7-T5 deferred. Keep E7-T6 historical transfer/import and E7-T7 HTTPS/auth/contact activation proposed; neither belongs in the anonymous synthetic overnight slice.

Revision 3 adds this ordered shared-edge sequence:

1. E7-T8 builds an inert, independently managed Nginx/Certbot topology and validates bootstrap, generated two-host configuration, renewal hooks, and failure behavior with fixtures only.
2. E7-T9 adds reversible cutover automation, a private WEF upstream path, unchanged AI Forecast host-upstream routing, inventories, smokes, atomic activation, and rollback without touching production.
3. E7-T10 performs the live DNS/ACME/listener cutover and captures sanitized evidence only after D-009 is resolved.

E7-T8 depends on completed E7-T4. E7-T9 stacks on E7-T8. E7-T10 remains proposed and excluded from executable implementation-plan revision 3 while D-009 is unresolved; resolving that gate requires promotion and an approved plan revision before live work.

## Task boundaries

- [E7-T1: Build production Compose topology](tasks/E7-T1-build-production-compose-topology.md) — promote first.
- [E7-T2: Provision and verify supplied server](tasks/E7-T2-provision-and-verify-supplied-server.md) — promote after E7-T1.
- [E7-T3: Implement GitHub image and deployment workflows](tasks/E7-T3-implement-github-image-and-deployment-workflows.md) — promote after E7-T2.
- [E7-T4: Implement health verification and rollback](tasks/E7-T4-implement-health-verification-and-rollback.md) — promote after E7-T3.
- [E7-T5: Future backup and restore capability](proposed-tasks/E7-T5-future-backup-and-restore-capability.md) — deferred until its named trigger.
- [E7-T6: Transfer and import the historical dataset](proposed-tasks/E7-T6-transfer-and-import-the-historical-dataset.md) — candidate boundary for spike refinement.
- [E7-T7: Enable production registration and contact reveal](proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) — candidate boundary for spike refinement.
- [E7-T8: Build isolated shared Nginx TLS topology](tasks/E7-T8-build-shared-nginx-tls-ingress.md) — first revision 3 implementation task.
- [E7-T9: Implement reversible shared-edge cutover](tasks/E7-T9-implement-reversible-shared-edge-cutover.md) — stack after E7-T8.
- [E7-T10: Roll out and verify shared TLS](proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md) — blocked by D-009 until live hostnames and forwarding are approved and proven.

Only promoted E7-T8 and E7-T9 may appear in implementation-plan revision 3. E7-T10 requires D-009 resolution, promotion, and a later approved plan revision.

## Risks and open questions

- A port/name/path collision can disrupt existing workloads.
- A partial/stale configuration transfer can activate an invalid release or leak secrets.
- GitHub hosted-runner startup failure can prevent image publication/deploy despite valid workflow syntax and local tests.
- PostGIS host bind ownership, an occupied port, memory pressure, or an invalid image digest must abort before existing runtime state changes.
- Plain HTTP cannot safely carry credentials or contact data; those routes/features remain absent.
- Historical transfer/import can exhaust storage or create unrecoverable changes without reconciliation and forward-safe migrations.
- Rollback cannot undo an incompatible database migration; E7-T1/T3 enforce forward-compatible migration-only release behavior and no automatic downgrade.
- Nginx cannot bind occupied 80/443 listeners; preflight must abort before changing either application route.
- Missing certificates create a bootstrap cycle; HTTP-only ACME configuration must validate independently before TLS virtual hosts are activated.
- A shared edge can make two healthy applications fail together; config validation, per-host probes, retained listeners, and atomic previous-config restoration are mandatory.
- Certbot dry-run skips deploy hooks unless explicitly requested; tests must cover both renewal and the validated success-only reload hook.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] E7-T1 through E7-T4 scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created during the spike.
- [x] E7-T8 through E7-T10 boundaries, dependencies, failure modes, tests, and D-009 gate are refined.
- [x] Revision 3 represents the approved material content.
- [x] Status and approval metadata record the delegated owner decision.

## Owner decision

Flippylolz approved revision 3 by accepting the attached E7 Shared TLS Stack plan and selecting the three-task split. This permits E7-T8/E7-T9 promotion and planning; E7-T10 remains blocked by D-009 and cannot be promoted or implemented until that gate and a current implementation plan are approved.
