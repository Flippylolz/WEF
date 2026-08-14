---
schema: ai-workflow/proposed-task@1
id: E7-T10
epic: E7
title: "Roll out and verify shared TLS"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M3
dependencies: [E7-T9]
requirement_ids: []
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-019, ADR-020]
deferred_decision_ids: [D-009]
source: "owner-approved-plan:2026-08-13-e7-shared-tls-stack"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T10: Roll out and verify shared TLS

> This live rollout remains planning input only. D-009, promotion, and a current implementation-plan approval are mandatory before any production mutation.

## Outcome

Activate and verify the independently managed shared Nginx/Certbot edge for WEF and AI Forecast on the supplied NUC, with valid public TLS, unattended renewal, independent health evidence, and rehearsed rollback.

## Scope

- Confirm two owner-approved public hostnames resolve to the NUC and public TCP 80/443 reaches it.
- Capture sanitized before inventory and verify current Caddy/3100 plus AI Forecast/3000 rollback paths.
- Start the isolated HTTP-only ACME edge, prove staging issuance, issue both production certificates, validate TLS config, and activate Nginx.
- Move WEF and AI Forecast routing in independently health-checked stages while retaining previous listeners/forwarding until each route passes.
- Enable matching HTTP-to-HTTPS redirects only after both HTTPS routes are healthy.
- Prove renewal dry run, success-only validated reload, external certificate chain/hostname/expiry, monitoring, and rollback.
- Capture sanitized after inventory and completion evidence without committing generated production configuration or certificate material.

## Out of scope

- Application behavior, images, database/API contracts, AI Forecast Compose/data ownership, DNS-01 plugins, paid DNS/certificates, backups, and sensitive WEF feature activation.
- Destructive cleanup of old listeners, certificate state, application data, Docker resources, or router rules without a separately reviewed owner action.

## Acceptance criteria

- [ ] D-009 records approved hostnames, matching DNS, confirmed 80/443 forwarding, staging issuance, and independent host routing evidence.
- [ ] Nginx is the only target public web server on 80/443 and every activation/reload follows a passing configuration validation.
- [ ] WEF and AI Forecast each have a distinct HTTPS hostname, valid public certificate chain, correct upstream route, and independent external health probe.
- [ ] HTTP redirects to the matching HTTPS hostname only after both HTTPS routes are healthy.
- [ ] Certbot retains complete persistent state, renews unattended, passes `renew --dry-run`, and reloads Nginx only through the validated success-only deploy hook.
- [ ] Certificate-expiry monitoring alerts before the renewal safety window is exhausted.
- [ ] WEF web/API/media/release-marker smoke passes without exposing Next.js/FastAPI ports.
- [ ] AI Forecast frontend/API remains healthy through cutover and rollback; its image, data, API behavior, and non-edge resources are unchanged.
- [ ] Before/after inventory proves DuckDNS, WireGuard, PostgreSQL, WEF persistence, and unrelated containers/networks/volumes are unchanged.
- [ ] DNS, certificate, validation, upstream, external-smoke, renewal, and reload failures abort or roll back without taking both applications offline.
- [ ] No certificate private key, ACME account secret, production hostname secret, generated Nginx environment, or sensitive host output is committed or uploaded.

## Dependencies and gates

- [E7-T9](../tasks/E7-T9-implement-reversible-shared-edge-cutover.md) must be done before live automation is trusted.
- [D-009](../../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md) requires two owner-approved hostnames plus DNS/router evidence.
- Promotion requires D-009 resolution, movement to `tasks/`, and a new approved E7 implementation-plan revision containing E7-T10.

## Rollout and rollback

Perform one bounded stage at a time and smoke both applications after each stage. On failure restore the previous validated Nginx config, listener/forwarding intent, and application route; preserve all application/database/certificate state and stop before removing rollback paths.

## Promotion checklist

- [ ] D-009 is resolved with owner-approved names and live DNS/80/443 evidence.
- [ ] E7-T9 is done with green CI and completed dependency evidence.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match approved spike revision 3.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] A current approved implementation plan contains E7-T10 and its current revision.
- [ ] Promotion metadata identifies the target, promoter, and timestamp.
