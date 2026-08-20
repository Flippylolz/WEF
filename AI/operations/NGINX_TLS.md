# Nginx and TLS Target

## Status

This is the approved target architecture from [ADR-020](../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md), not the current server state. The anonymous WEF rehearsal currently uses its isolated Caddy edge on port 3100, and AI Forecast currently publishes HTTP on port 3000. [E7-T8](../epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md) is complete on [PR #69](https://github.com/Flippylolz/WEF/pull/69): `infra/compose.shared-edge.yaml`, `infra/nginx/`, and the rendering/activation/renewal tooling under `scripts/deploy/`, proven by `make shared-edge-proof` with reserved `.test` hostnames and a local Pebble ACME server (an accidental gate invalidation recorded on 2026-08-15 was restored by the owner on 2026-08-16). [E7-T9](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md) is complete through PRs #106/#107 with fixture-proven cutover/rollback automation. [D-009](../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md) is resolved for a **WEF-only** initial cutover on `2fa54e2405.duckdns.org`; Forecast stays on `:3000`. Live mutation is gated [E7-T10](../epics/E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md).

## Target topology

- Nginx Open Source is the only public web server and reverse proxy on NUC ports 80/443 for WEF.
- Initial E7-T10 cutover terminates TLS for the WEF hostname only; Forecast remains on public host port 3000 (Forecast vhost stays optional in the renderer for fixtures/future use).
- Nginx routes WEF web, `/api/*`, and `/media/*` traffic to private WEF upstreams.
- Next.js, FastAPI, PostgreSQL, and workers are not public after the verified WEF cutover; Forecast continues on its existing `:3000` listener until a later owner-approved Forecast TLS task.
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

1. Confirm the owner-approved WEF hostname (`2fa54e2405.duckdns.org`), DNS resolution, and router forwarding for 80/443.
2. Inventory Nginx/Caddy/system listeners, Docker projects, AI Forecast 3000 health, WEF 3100 health, and all relevant persistent paths.
3. Start the isolated Nginx/Certbot edge without changing WEF or Forecast application upstreams.
4. Issue the WEF certificate, validate Nginx configuration, and prove WEF HTTPS.
5. Move WEF from Caddy to the Nginx route; preserve the prior WEF `:3100` listener until web/API/media/release-marker smoke passes.
6. Leave Forecast on `:3000` unchanged for this cutover; do not require a Forecast Nginx route.
7. Redirect HTTP to HTTPS for the WEF hostname only after WEF HTTPS is healthy.
8. Remove sole dependence on public `:3100` for WEF only after external HTTPS, renewal, monitoring, inventory, and rollback evidence pass.

On failure, restore the last healthy listener/routing configuration, reload the previously validated Nginx configuration, and verify WEF and Forecast independently. Never use global Docker cleanup or delete application/database state as part of ingress rollback.

## Required evidence

- Nginx configuration test and graceful reload.
- Valid public certificate chain and hostname match for both applications.
- HTTP-to-HTTPS redirect and conservative TLS/security-header checks.
- WEF web/API/media/release-marker smoke through Nginx.
- AI Forecast frontend/backend smoke through Nginx.
- Certbot renewal dry run, deploy-hook reload evidence, and expiry monitoring.
- Before/after inventory proving unrelated workloads and both applications' persistent state are unchanged.
- Deliberate invalid-config, unavailable-upstream, and renewal-hook failure tests with successful rollback.
