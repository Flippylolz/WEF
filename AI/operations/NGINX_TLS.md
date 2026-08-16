# Nginx and TLS Target

## Status

This is the approved target architecture from [ADR-020](../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md), not the current server state. The anonymous WEF rehearsal currently uses its isolated Caddy edge on port 3100, and AI Forecast currently publishes HTTP on port 3000. [E7-T8](../epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md) has built the inert topology (`infra/compose.shared-edge.yaml`, `infra/nginx/`, and the rendering/activation/renewal tooling under `scripts/deploy/`, proven by `make shared-edge-proof` with reserved `.test` hostnames and a local Pebble ACME server); [E7-T9](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md) may build cutover automation on top of it; no shared-ingress or existing-service mutation is authorized until gated [E7-T10](../epics/E7-production-delivery/proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md) is promoted.

## Target topology

- Nginx Open Source is the only public web server and reverse proxy on NUC ports 80/443.
- WEF and AI Forecast use separate public hostnames and independent Nginx server blocks.
- Nginx routes WEF web, `/api/*`, and `/media/*` traffic to private WEF upstreams.
- Nginx routes the AI Forecast hostname to its private frontend/API upstreams without changing application behavior or data.
- Next.js, FastAPI, PostgreSQL, workers, and AI Forecast application ports are not public after the verified cutover.
- The shared edge has its own project/path, configuration lifecycle, persistent certificate state, bounded logs, health checks, and rollback boundary; ordinary WEF releases do not own it.

## Free certificate lifecycle

- Use Certbot with Let's Encrypt; no paid certificate or paid DNS dependency is required.
- Prefer HTTP-01 with a shared read-only ACME webroot after router/firewall checks prove public ports 80/443 reach Nginx.
- Persist the complete Certbot state at `/etc/letsencrypt`; do not copy individual `live/` files or break Certbot-managed symlinks.
- Run unattended `certbot renew` on a bounded schedule.
- Use a success-only deploy hook to validate and gracefully reload Nginx after renewal.
- Require `certbot renew --dry-run`, external chain/hostname checks, expiry monitoring, and both application smokes before declaring renewal operational.
- Keep ACME account material and certificate private keys out of Git, CI logs, and artifacts.

## Migration and rollback

1. Confirm two owner-approved hostnames, DNS resolution, and router forwarding for 80/443.
2. Inventory Nginx/Caddy/system listeners, Docker projects, AI Forecast 3000/8080 health, WEF 3100 health, and all relevant persistent paths.
3. Start the isolated Nginx/Certbot edge without changing either application upstream.
4. Issue certificates, validate Nginx configuration, and prove both HTTPS hostnames.
5. Move WEF from Caddy to the Nginx route; preserve the prior WEF listener until web/API/media/release-marker smoke passes.
6. Move AI Forecast behind its Nginx route only under its owner-approved cutover; preserve a tested rollback to the direct port-3000 listener.
7. Redirect HTTP only after both HTTPS routes are healthy.
8. Remove public application-port exposure only after external HTTPS, renewal, monitoring, inventory, and rollback evidence pass.

On failure, restore the last healthy listener/routing configuration, reload the previously validated Nginx configuration, and verify both applications independently. Never use global Docker cleanup or delete application/database state as part of ingress rollback.

## Required evidence

- Nginx configuration test and graceful reload.
- Valid public certificate chain and hostname match for both applications.
- HTTP-to-HTTPS redirect and conservative TLS/security-header checks.
- WEF web/API/media/release-marker smoke through Nginx.
- AI Forecast frontend/backend smoke through Nginx.
- Certbot renewal dry run, deploy-hook reload evidence, and expiry monitoring.
- Before/after inventory proving unrelated workloads and both applications' persistent state are unchanged.
- Deliberate invalid-config, unavailable-upstream, and renewal-hook failure tests with successful rollback.
