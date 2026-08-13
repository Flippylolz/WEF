---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Docker/GitHub production delivery implementation plan"
status: approved
revision: 3
owner: owner
spike_revision: 3
task_sequence:
  - id: E7-T8
    revision: 2
  - id: E7-T9
    revision: 1
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

# Implementation Plan: Shared Nginx TLS delivery

## Approved spike baseline

[E7 spike revision 3](SPIKE.md) preserves completed E7-T1 through E7-T4 as the anonymous Caddy rehearsal and approves an isolated Nginx/Certbot target split into inert topology, reversible cutover automation, and live rollout.

[ADR-020](../../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md) selects the shared edge. [D-009](../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md) still blocks live hostnames, ACME issuance, public forwarding, and listener cutover. Therefore revision 3 authorizes only [E7-T8](tasks/E7-T8-build-shared-nginx-tls-ingress.md) and [E7-T9](tasks/E7-T9-implement-reversible-shared-edge-cutover.md); [E7-T10](proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md) remains proposed until D-009 is resolved and a later plan revision is approved.

## Scope and outcome

Deliver a locally proven, independently managed shared-edge topology plus host-safe cutover/rollback automation without mutating production. Nginx owns target ports 80/443 only after the future E7-T10 rollout. Certbot state, edge config, ACME webroot, and logs remain outside the ordinary WEF release boundary. Current Caddy/3100 and AI Forecast/3000 listeners remain active rollback paths throughout E7-T8/E7-T9.

## Ordered task sequence

### 1. E7-T8 — Build isolated shared Nginx TLS topology

- Task: [E7-T8 revision 2](tasks/E7-T8-build-shared-nginx-tls-ingress.md).
- Dependencies: completed E7-T4 release-health and rollback baseline.
- Independent result: inert shared-edge Compose boundary, HTTP-01 bootstrap, generated two-host Nginx config, persistent Certbot state, validated renewal hook, and local failure harness; no host or GitHub mutation.
- Verification: positive/negative Compose/config render, `nginx -t`, synthetic certificate files, two fixture host routes, least-privilege/static policy, renewal dry run, success-only reload hook, and secret exclusion.

### 2. E7-T9 — Implement reversible shared-edge cutover

- Task: [E7-T9 revision 1](tasks/E7-T9-implement-reversible-shared-edge-cutover.md).
- Dependencies: E7-T8 through direct stacked ancestry.
- Independent result: a cutover-safe WEF release variant, unchanged AI Forecast host-upstream route, before/after inventory, staged redirects, independent smokes, atomic edge activation, and previous-config/listener rollback; no production activation.
- Verification: local upstream fixtures, occupied-port/config/upstream failure injection, WEF API/media/release marker checks, AI Forecast frontend/API checks, atomic current/previous pointers, unchanged application data, and exact non-interference inventory.

## Deferred third task

[E7-T10](proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md) will execute DNS/ACME/listener cutover and capture live evidence after D-009. It is deliberately absent from `task_sequence`: unresolved deferred decisions prohibit promotion or executable planning. The intended branch stacks on E7-T9 only after the gate is resolved.

## Architecture and release invariants

- `wef-shared-edge` is a dedicated Compose project/path and lifecycle; ordinary `wef-production` deploys neither recreate nor remove it.
- The edge owns target host ports 80/443, generated Nginx configuration, ACME webroot, bounded logs, and complete persistent `/etc/letsencrypt` state.
- E7-T8/E7-T9 use fixtures and temporary local networks only. They do not bind production ports, issue public certificates, change router rules, or stop current listeners.
- Nginx starts in an HTTP-only bootstrap configuration for ACME. TLS server blocks activate only after required certificate files exist and `nginx -t` passes.
- WEF attaches to an explicitly managed external edge network through a cutover release variant; its web/API/media upstreams remain unpublished.
- AI Forecast remains owned by its existing project. The edge reaches its retained host listener through an explicit host-gateway upstream and never joins, recreates, or edits its project.
- Every generated edge release has immutable current/previous pointers. Activation validates files and upstreams before switching; rollback restores the previous validated config and listener state.
- Certbot uses saved webroot renewal settings, a persistent state tree, and a deploy hook that validates Nginx before graceful reload. The renewal dry run also exercises the hook explicitly.

## Security, privacy, and non-interference

- Interim HTTP serves anonymous synthetic data only. No account/session/contact/source/Telegram secret reaches it.
- SSH known-host material and private key stay in GitHub secrets; strict checking is mandatory.
- Fixture hostnames use reserved `.test` names and synthetic certificates. Production hostnames, ACME account data, private keys, and generated environment files never enter Git, CI logs, artifacts, or image layers.
- Nginx runs non-root with a read-only root filesystem, minimal writable tmp/log paths, dropped capabilities except the reviewed bind capability, and read-only configuration/certificate mounts.
- No edge command uses global prune, generic container names, `down -v`, or a path owned by an application project.
- Existing AI Forecast, DuckDNS, WireGuard, WEF persistence, and unrelated containers/networks/volumes/listeners are inventoried but never reconfigured by E7-T8/E7-T9.

## Test and verification strategy

- Repository: Markdown links, format/lint/type/tests/contracts/build/audits, Compose render, shell syntax/shellcheck, pinned images, and source/secret/image exclusions.
- Edge topology: positive/negative config fixtures, `nginx -t`, HTTP-01 path, distinct host routing, proxy headers, health checks, read-only mounts, capability/log limits, and persistent Certbot paths.
- Certificate lifecycle: non-interactive webroot command rendering, staging/dry-run behavior, success-only deploy hook, explicit dry-run hook execution, invalid-config refusal, and graceful reload.
- Cutover model: current/previous atomic pointers, occupied-port and unavailable-upstream aborts, independent WEF/AI Forecast smokes, redirect staging, previous-config restoration, and retained application listeners.
- Non-interference: exact before/after project/container/image/network/volume/listener/health comparison plus WEF database/media/release sentinel preservation.

## Rollout and rollback

Land E7-T8 and E7-T9 as direct stacked PRs after this documentation PR, waiting for green CI and triaged comments before creating each child. They produce inert artifacts and local evidence only. Keep Caddy/3100 and AI Forecast/3000 active in production.

After D-009 resolves, promote E7-T10 and approve a plan revision for the live sequence: inventory, start HTTP-only Nginx, prove ACME staging, issue both certificates, validate/activate HTTPS, smoke each host independently, move WEF, move AI Forecast forwarding, enable redirects, rehearse renewal/reload and rollback, then remove public application-port forwarding. Any failure restores the previous validated edge config and listener/forwarding state without deleting application or certificate data.

## Risks and mitigations

- **Bootstrap certificate cycle:** use a separately valid HTTP-only ACME configuration and activate TLS only after certificate files exist.
- **Port/path/project collision:** fail preflight before edge startup; explicitly check 80/443, dedicated paths/project, and external network ownership.
- **Secret leak through generated config/logs:** no shell tracing, mode-0600 temporary transfer, static log/artifact tests, atomic activation and cleanup.
- **One bad route takes down both applications:** validate config, probe both upstreams independently, retain old workers/listeners, and rollback on either failed smoke.
- **Certbot renews but Nginx keeps the old certificate:** success-only deploy hook performs `nginx -t` plus graceful reload; external expiry/serial checks remain E7-T10 evidence.
- **AI Forecast ownership leak:** proxy only to its retained host listener and compare its project resources before/after; never run Compose commands in its project.
- **Shared-host pressure:** conservative CPU/memory/log limits and abort thresholds; no historical import in this sequence.
- **Plain HTTP exposes sensitive behavior:** sensitive routes/features remain absent until E7-T10 verifies Nginx HTTPS and E7-T7 enables them.

## Invalidation triggers

Return to the spike for a different proxy/certificate authority, DNS-01 credentials/plugin, one-host path-prefix routing, shared application ownership, sensitive HTTP scope, or a new paid service. Return to this plan for material task order, edge path/network/upstream design, health contract, activation gate, or rollback changes.

## Approval checklist

- [x] E7 spike revision 3 is explicitly approved/current.
- [x] E7-T8 revision 2 and E7-T9 revision 1 are promoted with complete acceptance/traceability.
- [x] Dependencies are acyclic and enforceable through ordered stack ancestry.
- [x] Topology, host boundary, workflow gates, tests, migration compatibility, risks, rollout, and rollback are explicit.
- [x] D-009 remains attached to proposed E7-T10 and is not silently waived.
- [x] E7-T5 remains deferred; E7-T6/T7/T10 remain proposed and absent from the executable sequence.
- [x] No E7-T8/E7-T9 implementation code was written before revision 3 approval.
- [x] Revision 3 records the owner's accepted attached plan.

## Owner decision

Flippylolz approved revision 3 by accepting the attached E7 Shared TLS Stack plan and selecting E7-T8 topology, E7-T9 automation, and E7-T10 live rollout as separate task branches. Revision 3 authorizes only E7-T8/E7-T9; D-009 resolution and a later approved plan revision remain mandatory before E7-T10.
