---
schema: ai-workflow/proposed-task@1
id: E7-T8
epic: E7
title: "Build shared Nginx TLS ingress"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E7-T4]
requirement_ids: []
decision_ids: [ADR-010, ADR-014, ADR-019, ADR-020]
deferred_decision_ids: [D-009]
source: "owner-request:2026-08-13-nginx-tls"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E7-T8: Build shared Nginx TLS ingress

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Operate Nginx as the NUC's shared public web server with free, automatically renewed TLS for both WEF and the existing AI Forecast frontend currently exposed on host port 3000.

## Scope

- Add an isolated shared Nginx ingress that owns public ports 80/443 and proxies separate hostnames to WEF and AI Forecast private upstreams.
- Replace the WEF Caddy edge only after the Nginx route passes equivalent web/API/media, release-identity, and rollback checks.
- Obtain free Let's Encrypt certificates with Certbot, persist certificate state, schedule unattended renewal, and reload Nginx only after successful renewal.
- Inventory the existing AI Forecast topology and perform an explicitly approved, reversible cutover from its direct port-3000 public route to Nginx-terminated HTTPS.
- Add external HTTPS, certificate-expiry, renewal, upstream-health, redirect, security-header, and non-interference evidence.

## Out of scope

- Replacing Next.js or FastAPI as application servers.
- Changing AI Forecast application behavior, images, database, or API contracts.
- Enabling WEF registration, sessions, owner administration, or contact reveal; [E7-T7](E7-T7-enable-production-registration-and-contact-reveal.md) owns that gate after this task.
- Paid certificates, paid DNS, a staging environment, backup/restore implementation, or an unreviewed DNS-01 plugin.

## Work

- Resolve two stable public hostnames and verify both resolve to the NUC; prefer standard HTTPS on 443 over long-term public application ports.
- Define a dedicated shared-edge project/path, least-privilege Nginx runtime, read-only configuration, bounded logs, persistent `/etc/letsencrypt`, and explicit ownership.
- Configure port 80 for ACME HTTP-01 plus HTTPS redirects and port 443 for modern TLS, proxy headers, request IDs, timeouts, body limits, compression, and security headers.
- Use Certbot webroot issuance and unattended `certbot renew --deploy-hook <validated-nginx-reload>`.
- Keep WEF and AI Forecast rollback independent: a failed route/certificate/renewal check restores the previous listener and leaves both application/data projects unchanged.
- Update deploy and inventory automation so ordinary WEF releases neither recreate nor remove the shared edge.

## Acceptance criteria

- [ ] Nginx is the only target public web server on 80/443 and configuration validation passes before every reload.
- [ ] WEF and AI Forecast each have a distinct HTTPS hostname, valid public certificate chain, correct upstream route, and independent health probe.
- [ ] HTTP redirects to the matching HTTPS hostname only after both HTTPS routes are healthy.
- [ ] Certbot uses free Let's Encrypt issuance, persistent state, unattended renewal, a success-only Nginx reload hook, and a passing renewal dry run.
- [ ] Certificate-expiry monitoring alerts before the renewal safety window is exhausted.
- [ ] WEF web/API/media/release-marker smoke checks pass through Nginx, and its Caddy edge can be removed without exposing Next.js/FastAPI ports.
- [ ] AI Forecast remains healthy through cutover and rollback; its images, data, API behavior, and non-edge resources are unchanged.
- [ ] Before/after inventory proves DuckDNS, WireGuard, PostgreSQL, WEF persistence, and unrelated containers/networks/volumes are unchanged.
- [ ] Failure at DNS, certificate, Nginx validation, upstream health, or external smoke aborts or rolls back without taking both applications offline.
- [ ] No certificate private key, ACME account secret, production hostname secret, or generated Nginx environment file is committed or uploaded as a CI artifact.

## Dependencies and gates

- [E7-T4](../tasks/E7-T4-implement-health-verification-and-rollback.md) provides the WEF release health/rollback baseline that Nginx must preserve.
- [ADR-020](../../../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md) selects Nginx/Certbot and requires a controlled migration for the existing port-3000 service.
- [D-009](../../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md) must be resolved with two owner-approved hostnames and confirmed public 80/443 forwarding before promotion.
- E7 spike revision 2 did not evaluate this shared-edge task. A new owner-approved spike revision and implementation-plan revision are required before promotion or implementation.

## Risks and notes

- Nginx cannot take a listener already owned by AI Forecast; cutover order and rollback must avoid a port collision and preserve service availability.
- One hostname cannot independently route two root applications without path-prefix compatibility. Two hostnames are required unless a later approved spike proves both applications support path prefixes.
- The normal HTTP-01 flow requires public ports 80 and 443 to reach Nginx. DNS-01 requires a separate reviewed credential/plugin design.
- Certbot renewal success does not prove Nginx loaded the new certificate; post-hook validation and an external certificate check are both required.
- This task creates intentionally shared ingress, not shared application/data ownership.

## Promotion checklist

- [ ] E7 spike is revised to include the shared Nginx/Certbot topology and explicitly approved for that revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] D-009 hostname/router decision is resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
