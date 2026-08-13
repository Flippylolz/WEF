---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Docker/GitHub production delivery implementation plan"
status: approved
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E7-T1
    revision: 2
  - id: E7-T2
    revision: 2
  - id: E7-T3
    revision: 2
  - id: E7-T4
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T23:35:00Z"
  approved_revision: 2
  evidence: "Owner directive to prepare the MVP/autodeploy, choose safe defaults, log decisions/blockers, avoid non-WEF destruction, and continue stacking PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Anonymous synthetic production delivery

## Approved spike baseline

[E7 spike revision 2](SPIKE.md) approves an anonymous HTTP production-infrastructure rehearsal followed by immutable GitHub delivery and compatible application rollback. Historical import, backups, HTTPS/auth/contact/admin, and Telegram remain outside this sequence.

[ADR-020](../../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md) was accepted after this plan approval and selects Nginx/Certbot as the later shared TLS target. It does not alter the E7-T1 through E7-T4 Caddy rehearsal scope or authorize [E7-T8](proposed-tasks/E7-T8-build-shared-nginx-tls-ingress.md); that task requires a future approved spike and implementation-plan revision.

## Scope and outcome

Deliver a production Compose topology that is locally proven, prepared only under `/home/nuc/wef`, released as exact GHCR digests through a gated GitHub workflow, and rehearsed with healthy/unhealthy synthetic releases without modifying existing host workloads. Autodeploy remains disabled if B-006 prevents hosted evidence.

## Ordered task sequence

### 1. E7-T1 — Build production Compose topology

- Task: [E7-T1 revision 2](tasks/E7-T1-build-production-compose-topology.md).
- Dependencies: E1-T3 local topology and E5-T1 browser MVP are direct stacked ancestors.
- Independent result: inert production Compose/Caddy/scripts and local safety/rollback harness; no host or GitHub mutation.
- Verification: positive/negative Compose render, shell/static policy tests, production images, same-origin synthetic runtime, unhealthy rollback harness.

### 2. E7-T2 — Provision and verify supplied server

- Task: [E7-T2 revision 2](tasks/E7-T2-provision-and-verify-supplied-server.md).
- Dependencies: E7-T1 direct ancestry; D-001 resolved for anonymous rehearsal by ADR-019.
- Independent result: WEF-only directory/config boundary and redacted before/after host evidence.
- Verification: pinned SSH, capacity/port/config preflight, restrictive modes, unchanged existing projects/listeners/health, external 3100 probe only while listening.

### 3. E7-T3 — Implement GitHub image and deployment workflows

- Task: [E7-T3 revision 2](tasks/E7-T3-implement-github-image-and-deployment-workflows.md).
- Dependencies: E1-T4 CI plus E7-T1/T2 direct ancestry.
- Independent result: exact-image publication and gated/locked complete-config delivery review, with auto deploy still false.
- Verification: actionlint/static gate matrix, complete local release commands, secret/source exclusion, hosted manual release when B-006 permits.

### 4. E7-T4 — Implement health verification and rollback

- Task: [E7-T4 revision 2](tasks/E7-T4-implement-health-verification-and-rollback.md).
- Dependencies: E7-T3 direct ancestry.
- Independent result: healthy production rehearsal, deliberate failure, restored prior app release, and evidence-gated autodeploy enablement.
- Verification: public synthetic map/API/release identity, persistence sentinel, unhealthy timeout/rollback, existing-workload inventory diff, no Alembic downgrade.

## Architecture and release invariants

- `wef-production` is the only Compose project targeted; Caddy alone publishes configured port 3100.
- Web/API/PostGIS use internal networking. Persistent database/media/Caddy/release/config state remains under `/home/nuc/wef`.
- GitHub builds exact source SHAs; production consumes explicit image digests. The server never builds source.
- Complete config is reconstructed from Actions variables/secrets each deploy, validated, transferred to a temporary 0600 release directory, and atomically activated.
- One host `flock` and one Actions concurrency group serialize releases.
- Migration runs before app replacement and must remain backward-compatible with the retained previous app. Rollback switches application manifests only and never automatically downgrades data.
- Synthetic production seed is permitted only through an explicit rehearsal flag added within E7-T1; normal production remains fail-closed.

## Security, privacy, and non-interference

- Interim HTTP serves anonymous synthetic data only. No account/session/contact/source/Telegram secret reaches it.
- SSH known-host material and private key stay in GitHub secrets; strict checking is mandatory.
- Workflows use minimum permissions and pinned third-party action commits. PR-originated code cannot receive deploy secrets or run SSH.
- No deploy command uses global prune, generic container names, `down -v`, or a path outside `/home/nuc/wef`.
- Existing AI Forecast, DuckDNS, WireGuard containers/networks/volumes/listeners are inventoried but never reconfigured.

## Test and verification strategy

- Repository: format/lint/type/tests/contracts/build/audits, actionlint, Markdown links, Compose render, source/secret/image exclusions.
- Release model: config schema/negative fixtures, immutable-digest/port/network/path/static shell policies, temporary release-state integration harness.
- Host: before/after inventory, port/capacity/permission preflight, remote Compose render, existing service health.
- Delivery: event/origin/enable/manual-SHA gate matrix, full local release command equivalence, hosted GHCR/digest/SSH evidence when B-006 permits.
- Rollback: known healthy release, deliberately unhealthy app release, bounded failure, previous manifest restoration, persistence and existing-workload verification.

## Rollout and rollback

Land each task as a stacked PR. Keep `AUTO_DEPLOY_ENABLED=false`. E7-T2 may prepare the WEF boundary before GHCR is available but does not claim a running release. E7-T3 may run manual dispatch only after hosted Actions starts. E7-T4 alone may enable automatic main deployment after both healthy and unhealthy rollback rehearsals pass. On any failure, leave auto deploy false, preserve WEF data, and modify no non-WEF resource.

## Risks and mitigations

- **Hosted jobs never start:** keep B-006 active, locally validate artifacts, do not enable auto deploy or claim operational delivery.
- **Port/path/project collision:** fail preflight before Compose pull/up; explicit project/path/port checks.
- **Secret leak through generated config/logs:** no shell tracing, mode-0600 temporary transfer, static log/artifact tests, atomic activation and cleanup.
- **Migration breaks rollback:** expand-compatible migrations only, previous-app compatibility test, no automatic downgrade.
- **Unhealthy replacement causes outage:** pull first, retain manifest/images/config, bounded health timeout and automatic app rollback.
- **Shared-host pressure:** conservative CPU/memory/log limits and abort thresholds; no historical import in this sequence.
- **Plain HTTP exposes sensitive behavior:** sensitive routes/features remain absent until the separately approved E7-T8 Nginx HTTPS migration and E7-T7 enablement; both remain outside this plan revision.

## Invalidation triggers

Return to the spike for a different host/orchestrator/registry, self-hosted runner, sensitive HTTP scope, destructive migration/restore policy, shared project/port, or new external paid service. Return to this plan for material task order, config source, health contract, release gate, or rollback changes.

## Approval checklist

- [x] E7 spike revision 2 is explicitly approved/current.
- [x] E7-T1 through E7-T4 revision 2 are promoted with complete acceptance/traceability.
- [x] Dependencies are acyclic and enforceable through ordered stack ancestry.
- [x] Topology, host boundary, workflow gates, tests, migration compatibility, risks, rollout, and rollback are explicit.
- [x] D-001 is resolved for the anonymous rehearsal; B-006 is an evidence blocker, not silently waived.
- [x] E7-T5/T6/T7 remain deferred/proposed and absent from the executable sequence.
- [x] No implementation code was written before revision 2 approval.
- [x] Revision 2 records the delegated owner approval.

## Owner decision

Flippylolz approved revision 2 through the delegated overnight MVP/autodeploy directive. E7-T1 through E7-T4 still start in order on dedicated stacked branches; B-006, hosted evidence, and server non-interference remain mandatory completion gates.
