---
schema: ai-docs/adr@1
id: ADR-020
title: Use Nginx as the shared TLS ingress
status: accepted
date: 2026-08-13
supersedes: [ADR-010]
superseded_by: []
resolves: []
---

# ADR-020: Use Nginx as the shared TLS ingress

- Status: accepted
- Date: 2026-08-13
- Decision: use Nginx Open Source as the NUC's target public web server and reverse proxy. A shared Nginx edge will terminate TLS for both WEF and the existing AI Forecast frontend currently exposed on host port 3000, while Next.js and the existing application servers remain private upstreams.
- Certificate lifecycle: use free Let's Encrypt certificates obtained by Certbot. Persist `/etc/letsencrypt`, run unattended `certbot renew`, reload Nginx only through a successful-renewal deploy hook, and prove renewal with `certbot renew --dry-run`.
- Routing: use separate public hostnames on standard ports 80/443 rather than exposing application-server ports as the long-term public interface. [D-009](../deferred/D-009-shared-tls-hostnames-and-forwarding.md) gates final hostnames and router forwarding; HTTP redirects to HTTPS only after both HTTPS routes pass smoke checks.
- Migration:
  - The implemented anonymous WEF rehearsal may continue using its isolated Caddy edge on port 3100 until the shared-ingress task is approved and completed.
  - The migration replaces Caddy with Nginx for WEF public routing and adds the existing AI Forecast frontend as a second TLS-terminated upstream.
  - Existing AI Forecast port 3000 remains untouched until an inventory, owner-approved cutover plan, independent health probes, and rollback have been rehearsed.
- Isolation: Nginx/Certbot configuration, certificate state, and logs use a dedicated shared-edge boundary. WEF application deploys must not recreate or remove shared ingress or AI Forecast resources.
- Partial supersession: [ADR-010](ADR-010-isolate-wef-shared-nuc.md) remains authoritative for WEF database, application, persistence, project, and cleanup isolation. This record supersedes only its assumption that WEF's own edge permanently owns the sole public application port and its blanket prohibition on a reviewed shared-edge migration.
- Consequences:
  - Nginx is the target edge web server; Next.js remains the WEF application server and FastAPI remains the API server.
  - Ports 80 and 443 must reach the NUC for normal HTTP-01/TLS operation unless a separately reviewed DNS-01 design is selected.
  - Certificate renewal, expiry monitoring, configuration validation, graceful reload, both application smoke checks, and rollback evidence become public-launch gates.
  - No Nginx, Certbot, router, existing-project, or port-3000 mutation is authorized by this ADR alone. [E7-T8](../../epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md) and [E7-T9](../../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md) are inert implementation tasks; [E7-T10](../../epics/E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md) owns the gated live mutation.

## Owner amendment (2026-08-20)

- Owner resolved [D-009](../deferred/D-009-shared-tls-hostnames-and-forwarding.md) with **WEF-only** shared TLS on `2fa54e2405.duckdns.org`.
- AI Forecast remains on public host port **3000** for this cutover and is **not** required to receive a second hostname or Nginx TLS termination in E7-T10 revision 2.
- Dual-origin Forecast HTTPS remains a later, separately approved change; it does not block WEF HTTPS or E7-T7 once WEF TLS is verified.
- Routing sentence above that required separate public hostnames for both apps is narrowed for the initial cutover by this amendment; the WEF hostname-on-443 requirement stands.
